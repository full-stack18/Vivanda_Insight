from getpass import getpass
import argparse
import csv
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    sys.exit(
        "Falta el conector de PostgreSQL. Instálalo con: "
        "py -3.11 -m pip install psycopg2-binary"
    )


PROJECT_DIR = Path(__file__).resolve().parents[1]
DBT_DIR = PROJECT_DIR / "dbt" / "vivanda_dbt"
DBT_EXE = DBT_DIR / ".venv" / "Scripts" / "dbt.exe"
BUCKET = "vivanda-dw-undc-2026-0864"
VIVANDA_INSIGHT_DATA_DIR = PROJECT_DIR / "vivanda_insight" / "data"
MART_EXPORTS = [
    {
        "table": "VIVANDA_DW.GOLD.MART_VENTAS_MENSUALES",
        "file": "mart_ventas_mensuales.csv",
        "columns": [
            "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "SEDE",
            "NUMERO_VENTAS", "SUBTOTAL_VENTAS", "DESCUENTOS", "VENTAS_NETAS",
        ],
        "order_by": "ANIO, MES_NUMERO, ID_SEDE",
    },
    {
        "table": "VIVANDA_DW.GOLD.MART_VENTAS_PRODUCTOS",
        "file": "mart_ventas_productos.csv",
        "columns": [
            "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "ID_PRODUCTO", "SKU",
            "PRODUCTO", "ID_CATEGORIA", "CATEGORIA", "UNIDADES_VENDIDAS",
            "SUBTOTAL_VENTAS", "DESCUENTOS", "VENTAS_NETAS", "NUMERO_VENTAS",
        ],
        "order_by": "ANIO, MES_NUMERO, ID_SEDE, VENTAS_NETAS DESC",
    },
    {
        "table": "VIVANDA_DW.GOLD.MART_PAGOS_METODO",
        "file": "mart_pagos_metodo.csv",
        "columns": [
            "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "ID_METODO_PAGO",
            "METODO_PAGO", "NUMERO_PAGOS", "NUMERO_VENTAS", "TOTAL_PAGADO",
        ],
        "order_by": "ANIO, MES_NUMERO, ID_SEDE, TOTAL_PAGADO DESC",
    },
    
    {
        "table": "VIVANDA_DW.GOLD.MART_INVENTARIO_ACTUAL",
        "file": "mart_inventario_actual.csv",
        "columns": [
            "ID_INVENTARIO", "ID_PRODUCTO", "SKU", "PRODUCTO",
            "ID_CATEGORIA", "CATEGORIA", "ID_ALMACEN", "ALMACEN",
            "ID_SEDE", "SEDE", "STOCK_ACTUAL", "STOCK_MINIMO",
            "ESTADO_STOCK", "ACTUALIZADO_EN",
        ],
        "order_by": "PRODUCTO, ALMACEN",
    },
    {
        "table": "VIVANDA_DW.GOLD.MART_COMPRAS_MENSUALES",
        "file": "mart_compras_mensuales.csv",
        "columns": [
            "ANIO",
            "MES_NUMERO",
            "MES",
            "ID_SEDE",
            "SEDE",
            "ID_ALMACEN",
            "ALMACEN",
            "ID_PROVEEDOR",
            "PROVEEDOR",
            "ESTADO_COMPRA",
            "NUMERO_COMPRAS",
            "UNIDADES_COMPRADAS",
            "TOTAL_COMPRADO",
        ],
        "order_by": "ANIO, MES_NUMERO, ID_SEDE, PROVEEDOR, TOTAL_COMPRADO DESC",
    },
]

# Se extraen las mismas 15 tablas que ya consume Bronze.
TABLE_FILES = [
    "almacen.csv",
    "compra.csv",
    "detalle_compra.csv",
    "categoria.csv",
    "cliente.csv",
    "detalle_venta.csv",
    "empleado.csv",
    "inventario.csv",
    "metodo_pago.csv",
    "movimiento_inventario.csv",
    "pago.csv",
    "producto.csv",
    "proveedor.csv",
    "sede.csv",
    "venta.csv",
]

# detalle_venta en Bronze consume estas seis columnas. El OLTP también tiene
# total_linea, pero no se exporta para conservar el formato CSV ya existente.
EXPORT_COLUMNS = {
    "detalle_venta": (
        "id_detalle",
        "id_venta",
        "id_producto",
        "cantidad",
        "precio_unitario",
        "descuento",
    ),
    
    "detalle_compra": (
    "id_detalle",
    "id_compra",
    "id_producto",
    "cantidad",
    "costo_unitario",
    ),
}

STAGING_MODELS = [
    "stg_almacen",
    "stg_categoria",
    "stg_cliente",
    "stg_compra",
    "stg_detalle_compra",
    "stg_detalle_venta",
    "stg_empleado",
    "stg_inventario",
    "stg_metodo_pago",
    "stg_movimiento_inventario",
    "stg_pago",
    "stg_producto",
    "stg_proveedor",
    "stg_sede",
    "stg_venta",
]


def run_step(title, command, cwd=None, env=None):
    print(f"\n--- {title} ---")
    subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
    )


def _rows_from_dbt_json(output):
    """Obtiene las filas del formato JSON de `dbt show`."""
    candidates = []

    def add_candidate(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            candidates.append(value)
        elif isinstance(value, dict):
            for key in ("show", "preview", "rows"):
                if key in value:
                    add_candidate(value[key])

    try:
        add_candidate(json.loads(output))
    except json.JSONDecodeError:
        pass

    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            data = event.get("data", {})
            if isinstance(data, dict):
                add_candidate(data.get("preview"))
            info = event.get("info", {})
            if isinstance(info, dict):
                add_candidate(info.get("msg"))

    if candidates:
        return candidates[-1]
    raise ValueError(
        "dbt terminó sin devolver filas JSON reconocibles para el mart."
    )


def export_mart_to_csv(env, table, columns, order_by, csv_path):
    """Exporta un mart con cabeceras validadas y reemplazo atómico del CSV."""
    column_list = ", ".join(columns)
    query = f"SELECT {column_list} FROM {table} ORDER BY {order_by}"
    command = [
        DBT_EXE,
        "show",
        "--inline",
        query,
        "--limit",
        "100000",
        "--output",
        "json",
        "--log-format",
        "json",
    ]

    print(f"\n--- Exportando {table.rsplit('.', 1)[-1]} para Vivanda Insight ---")
    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(DBT_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        detail = "\n".join(detail[-12:])
        raise RuntimeError(
            f"No se pudo leer {table} desde Snowflake con dbt show. "
            f"El CSV actual {csv_path.name} se conserva.\n{detail}"
        )

    rows = _rows_from_dbt_json(result.stdout + "\n" + result.stderr)
    normalized_rows = []
    expected_columns = {column.upper() for column in columns}
    for row in rows:
        normalized = {str(key).upper(): value for key, value in row.items()}
        missing = expected_columns.difference(normalized)
        if missing:
            raise ValueError(
                "El mart no contiene todas las columnas que necesita Vivanda "
                f"Insight. Faltan: {', '.join(sorted(missing))}."
            )
        normalized_rows.append(
            {column: normalized[column] for column in columns}
        )

    if not normalized_rows:
        raise ValueError(
            f"{table} no devolvió registros; se conserva el CSV actual {csv_path.name}."
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_csv = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=csv_path.parent,
            prefix=f"{csv_path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_csv = Path(output.name)
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(normalized_rows)
        os.replace(temporary_csv, csv_path)
    finally:
        if temporary_csv is not None and temporary_csv.exists():
            temporary_csv.unlink()

    print(
        f"Vivanda Insight actualizado: {len(normalized_rows):,} filas -> "
        f"{csv_path}"
    )


def export_marts_to_vivanda_insight(env):
    for mart in MART_EXPORTS:
        export_mart_to_csv(
            env=env,
            table=mart["table"],
            columns=mart["columns"],
            order_by=mart["order_by"],
            csv_path=VIVANDA_INSIGHT_DATA_DIR / mart["file"],
        )


def extract_postgres_to_csv(csv_dir):
    host = input("Endpoint de PostgreSQL RDS: ").strip()
    if not host:
        sys.exit("Debes indicar el endpoint de PostgreSQL RDS.")

    port = os.environ.get("VIVANDA_PGPORT", "5432")
    database = os.environ.get("VIVANDA_PGDATABASE", "vivanda_oltp")
    user = os.environ.get("VIVANDA_PGUSER", "postgres")
    password = getpass("Contraseña de PostgreSQL (no se mostrará): ")
    if not password:
        sys.exit("No ingresaste la contraseña de PostgreSQL.")

    print("\n--- Extrayendo tablas del OLTP PostgreSQL a CSV ---")
    try:
        with psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=20,
        ) as connection:
            with connection.cursor() as cursor:
                for filename in TABLE_FILES:
                    table_name = Path(filename).stem
                    columns = EXPORT_COLUMNS.get(table_name)
                    selected_columns = (
                        sql.SQL(", ").join(sql.Identifier(column) for column in columns)
                        if columns
                        else sql.SQL("*")
                    )
                    query = sql.SQL(
                        "COPY (SELECT {columns} FROM {schema}.{table} ORDER BY 1) "
                        "TO STDOUT WITH (FORMAT CSV, HEADER TRUE)"
                    ).format(
                        columns=selected_columns,
                        schema=sql.Identifier("public"),
                        table=sql.Identifier(table_name),
                    )
                    output_path = csv_dir / filename
                    with output_path.open("w", encoding="utf-8", newline="") as output:
                        cursor.copy_expert(query.as_string(connection), output)
                    if output_path.stat().st_size == 0:
                        sys.exit(f"La extracción generó un CSV vacío: {filename}")
                    print(f"Extraído: {table_name} -> {filename}")
    except psycopg2.Error as exc:
        detail = exc.pgerror or str(exc).splitlines()[0]
        sys.exit(
            "No se pudo extraer PostgreSQL. Revisa endpoint, puerto, base, "
            f"usuario, contraseña y acceso de red. Detalle: {detail}"
        )


def check_aws_session():
    if shutil.which("aws") is None:
        sys.exit("No encuentro AWS CLI en PATH.")

    aws_check = subprocess.run(
        ["aws", "sts", "get-caller-identity"],
        capture_output=True,
        text=True,
    )
    if aws_check.returncode != 0:
        sys.exit(
            "No hay una sesión AWS activa. Ejecuta "
            "'aws login --region us-east-2' y vuelve a iniciar el script."
        )


def refresh_insight_marts_only():
    """Reconstruye y exporta solo los marts locales de Vivanda Insight."""
    if not DBT_EXE.is_file():
        sys.exit(f"No encuentro dbt: {DBT_EXE}")

    env = os.environ.copy()
    env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"] = getpass(
        "Contraseña de Snowflake (no se mostrará): "
    )
    if not env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"]:
        sys.exit("No ingresaste la contraseña de Snowflake.")

    run_step(
        "Reconstruyendo solo los marts de Vivanda Insight",
        [
            DBT_EXE,
            "run",
            "--select",
            "mart_ventas_mensuales",
            "mart_ventas_productos",
            "mart_pagos_metodo",
            "mart_compras_mensuales",
            "mart_inventario_actual",
        ],
        cwd=DBT_DIR,
        env=env,
    )
    export_marts_to_vivanda_insight(env)
    print("\nMarts de Vivanda Insight actualizados sin recargar PostgreSQL ni S3.")


def export_insight_marts_only():
    """Exporta los marts Gold existentes sin volver a ejecutar modelos dbt."""
    if not DBT_EXE.is_file():
        sys.exit(f"No encuentro dbt: {DBT_EXE}")

    env = os.environ.copy()
    env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"] = getpass(
        "Contraseña de Snowflake (no se mostrará): "
    )
    if not env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"]:
        sys.exit("No ingresaste la contraseña de Snowflake.")

    export_marts_to_vivanda_insight(env)
    print("\nCSV de Vivanda Insight exportados desde los marts existentes en GOLD.")


def main():
    if not DBT_EXE.is_file():
        sys.exit(f"No encuentro dbt: {DBT_EXE}")

    check_aws_session()

    env = os.environ.copy()
    env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"] = getpass(
        "Contraseña de Snowflake (no se mostrará): "
    )
    if not env["DBT_ENV_SECRET_SNOWFLAKE_PASSWORD"]:
        sys.exit("No ingresaste la contraseña de Snowflake.")

    # Los CSV se generan en una carpeta temporal, sin reemplazar los archivos
    # originales que antes se guardaban en Downloads.
    with tempfile.TemporaryDirectory(prefix="vivanda_oltp_export_") as temp_dir:
        csv_dir = Path(temp_dir)
        extract_postgres_to_csv(csv_dir)

        for filename in TABLE_FILES:
            local_file = csv_dir / filename
            destination = f"s3://{BUCKET}/bronze/{filename}"
            run_step(
                f"Subiendo {filename} a S3",
                ["aws", "s3", "cp", local_file, destination],
                env=env,
            )

        run_step(
            "Recargando las 15 tablas Bronze",
            [DBT_EXE, "run-operation", "load_bronze_from_s3"],
            cwd=DBT_DIR,
            env=env,
        )

        run_step(
            "Actualizando modelos de staging",
            [DBT_EXE, "run", "--select", *STAGING_MODELS],
            cwd=DBT_DIR,
            env=env,
        )

        run_step(
            "Actualizando snapshot SCD2",
            [DBT_EXE, "snapshot"],
            cwd=DBT_DIR,
            env=env,
        )

        run_step(
            "Ejecutando modelos analíticos",
            [DBT_EXE, "run", "--exclude", "path:models/example"],
            cwd=DBT_DIR,
            env=env,
        )

        run_step(
            "Validando pruebas de calidad",
            [DBT_EXE, "test", "--exclude", "path:models/example"],
            cwd=DBT_DIR,
            env=env,
        )

        export_marts_to_vivanda_insight(env)

    print("\nPipeline finalizado correctamente.")
    print("Actualiza el informe de Power BI para cargar los datos nuevos de GOLD.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestador de datos Vivanda")
    parser.add_argument(
        "--refresh-insight-marts",
        action="store_true",
        help=(
            "Reconstruye y exporta solo los marts de Vivanda Insight; "
            "omite extracción OLTP, carga S3, snapshot y pruebas completas."
        ),
    )
    parser.add_argument(
        "--export-insight-marts-only",
        action="store_true",
        help=(
            "Solo exporta los CSV desde los marts Gold existentes; "
            "no ejecuta modelos dbt ni recarga OLTP/S3."
        ),
    )
    arguments = parser.parse_args()
    if arguments.export_insight_marts_only:
        export_insight_marts_only()
    elif arguments.refresh_insight_marts:
        refresh_insight_marts_only()
    else:
        main()
