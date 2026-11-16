from pathlib import Path

import duckdb
import altair as alt
import pandas as pd
import streamlit as st
import re
import requests
from theme import aplicar_marca_vivanda


st.set_page_config(
    page_title="Vivanda Insight",
    page_icon="🛒",
    layout="wide",
)

aplicar_marca_vivanda()

st.info(
    "Demo académica con datos simulados de ventas, productos y pagos. "
    "Pregunta por sedes, periodos, categorías, productos o métodos de pago. "
    "El asistente consulta los datos localmente con Ollama y DuckDB."
)

# Lee el CSV desde vivanda_insight/data/
archivo_csv = Path(__file__).parent / "data" / "mart_ventas_mensuales.csv"

if not archivo_csv.exists():
    st.error(f"No encuentro el archivo: {archivo_csv}")
    st.stop()

df = pd.read_csv(archivo_csv, encoding="utf-8-sig")

columnas_requeridas = [
    "ANIO",
    "MES_NUMERO",
    "MES",
    "ID_SEDE",
    "SEDE",
    "NUMERO_VENTAS",
    "SUBTOTAL_VENTAS",
    "DESCUENTOS",
    "VENTAS_NETAS",
]

faltantes = [col for col in columnas_requeridas if col not in df.columns]

if faltantes:
    st.error(f"Al CSV le faltan estas columnas: {', '.join(faltantes)}")
    st.write("Columnas encontradas:", list(df.columns))
    st.stop()

columnas_numericas = [
    "ANIO",
    "MES_NUMERO",
    "ID_SEDE",
    "NUMERO_VENTAS",
    "SUBTOTAL_VENTAS",
    "DESCUENTOS",
    "VENTAS_NETAS",
]

for columna in columnas_numericas:
    df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0)


def cargar_mart_opcional(nombre_archivo, columnas_requeridas, columnas_numericas):
    ruta = Path(__file__).parent / "data" / nombre_archivo
    if not ruta.exists():
        return pd.DataFrame()

    datos_mart = pd.read_csv(ruta, encoding="utf-8-sig")
    faltantes_mart = [
        columna
        for columna in columnas_requeridas
        if columna not in datos_mart.columns
    ]
    if faltantes_mart:
        st.error(
            f"A {nombre_archivo} le faltan estas columnas: "
            f"{', '.join(faltantes_mart)}"
        )
        st.stop()

    for columna in columnas_numericas:
        datos_mart[columna] = pd.to_numeric(
            datos_mart[columna], errors="coerce"
        ).fillna(0)
    return datos_mart


df_productos = cargar_mart_opcional(
    "mart_ventas_productos.csv",
    [
        "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "ID_PRODUCTO", "SKU",
        "PRODUCTO", "ID_CATEGORIA", "CATEGORIA", "UNIDADES_VENDIDAS",
        "SUBTOTAL_VENTAS", "DESCUENTOS", "VENTAS_NETAS", "NUMERO_VENTAS",
    ],
    [
        "ANIO", "MES_NUMERO", "ID_SEDE", "ID_PRODUCTO", "ID_CATEGORIA",
        "UNIDADES_VENDIDAS", "SUBTOTAL_VENTAS", "DESCUENTOS",
        "VENTAS_NETAS", "NUMERO_VENTAS",
    ],
)

df_pagos = cargar_mart_opcional(
    "mart_pagos_metodo.csv",
    [
        "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "ID_METODO_PAGO",
        "METODO_PAGO", "NUMERO_PAGOS", "NUMERO_VENTAS", "TOTAL_PAGADO",
    ],
    [
        "ANIO", "MES_NUMERO", "ID_SEDE", "ID_METODO_PAGO",
        "NUMERO_PAGOS", "NUMERO_VENTAS", "TOTAL_PAGADO",
    ],
)

df_compras = cargar_mart_opcional(
    "mart_compras_mensuales.csv",
    [
        "ANIO", "MES_NUMERO", "MES", "ID_SEDE", "SEDE",
        "ID_ALMACEN", "ALMACEN", "ID_PROVEEDOR", "PROVEEDOR",
        "ESTADO_COMPRA", "NUMERO_COMPRAS", "UNIDADES_COMPRADAS",
        "TOTAL_COMPRADO",
    ],
    [
        "ANIO", "MES_NUMERO", "ID_SEDE", "ID_ALMACEN",
        "ID_PROVEEDOR", "NUMERO_COMPRAS", "UNIDADES_COMPRADAS",
        "TOTAL_COMPRADO",
    ],
)

# DuckDB consulta los datos localmente, sin conectarse a Snowflake.
conexion = duckdb.connect(":memory:")
conexion.register("datos_csv", df)
conexion.execute("CREATE TABLE ventas AS SELECT * FROM datos_csv")

sedes = ["Todas"] + sorted(df["SEDE"].dropna().astype(str).unique().tolist())
sede_elegida = st.sidebar.selectbox("Filtrar por sede", sedes)

anios_disponibles = sorted(df["ANIO"].dropna().astype(int).unique().tolist())
anio_elegido = st.sidebar.selectbox(
    "Filtrar por año", ["Todos"] + anios_disponibles
)

datos_periodo = df.copy()
if anio_elegido != "Todos":
    datos_periodo = datos_periodo[datos_periodo["ANIO"] == int(anio_elegido)]

meses_disponibles = (
    datos_periodo.sort_values("MES_NUMERO")["MES"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
mes_elegido = st.sidebar.selectbox(
    "Filtrar por mes", ["Todos"] + meses_disponibles
)

datos = datos_periodo.copy()
if mes_elegido != "Todos":
    datos = datos[datos["MES"].astype(str) == mes_elegido]

if sede_elegida == "Todas":
    id_sede_elegida = None
else:
    datos = datos[datos["SEDE"].astype(str) == sede_elegida]
    coincidencias_sede = df.loc[
        df["SEDE"].astype(str) == sede_elegida, "ID_SEDE"
    ].dropna()
    id_sede_elegida = int(coincidencias_sede.iloc[0]) if not coincidencias_sede.empty else None


def filtrar_mart(datos_mart):
    resultado = datos_mart.copy()
    if resultado.empty:
        return resultado

    if id_sede_elegida is not None and "ID_SEDE" in resultado.columns:
        resultado = resultado[
            pd.to_numeric(resultado["ID_SEDE"], errors="coerce")
            == id_sede_elegida
        ]
    if anio_elegido != "Todos" and "ANIO" in resultado.columns:
        resultado = resultado[
            pd.to_numeric(resultado["ANIO"], errors="coerce")
            == int(anio_elegido)
        ]
    if mes_elegido != "Todos" and "MES" in resultado.columns:
        resultado = resultado[resultado["MES"].astype(str) == mes_elegido]
    return resultado.copy()


datos_productos = filtrar_mart(df_productos)
datos_pagos = filtrar_mart(df_pagos)
datos_compras = filtrar_mart(df_compras)

conexion.register("datos_filtrados", datos)
conexion.execute(
    "CREATE OR REPLACE TEMP TABLE ventas_filtradas AS "
    "SELECT * FROM datos_filtrados"
)

tablas_permitidas = {"ventas_filtradas"}
if not datos_productos.empty:
    conexion.register("datos_productos_filtrados", datos_productos)
    conexion.execute(
        "CREATE OR REPLACE TEMP TABLE productos_filtrados AS "
        "SELECT * FROM datos_productos_filtrados"
    )
    tablas_permitidas.add("productos_filtrados")

if not datos_pagos.empty:
    conexion.register("datos_pagos_filtrados", datos_pagos)
    conexion.execute(
        "CREATE OR REPLACE TEMP TABLE pagos_filtrados AS "
        "SELECT * FROM datos_pagos_filtrados"
    )
    tablas_permitidas.add("pagos_filtrados")
    
if not datos_compras.empty:
    conexion.register("datos_compras_filtrados", datos_compras)
    conexion.execute(
        "CREATE OR REPLACE TEMP TABLE compras_filtradas AS "
        "SELECT * FROM datos_compras_filtrados"
    )
    tablas_permitidas.add("compras_filtradas")

registros, numero_ventas, ventas_netas, descuentos = conexion.execute(
    """
    SELECT
        COUNT(*),
        COALESCE(SUM(NUMERO_VENTAS), 0),
        COALESCE(SUM(VENTAS_NETAS), 0),
        COALESCE(SUM(DESCUENTOS), 0)
    FROM ventas_filtradas
    """
).fetchone()

variacion_mensual = None
etiqueta_variacion = None
mensaje_variacion = None

if anio_elegido != "Todos" and mes_elegido != "Todos":
    periodo_actual = datos_periodo.loc[
        datos_periodo["MES"].astype(str) == mes_elegido,
        ["ANIO", "MES_NUMERO"],
    ].drop_duplicates()
    if not periodo_actual.empty:
        anio_actual = int(anio_elegido)
        mes_actual = int(periodo_actual.iloc[0]["MES_NUMERO"])
        periodo = pd.Period(year=anio_actual, month=mes_actual, freq="M")
        periodo_anterior = periodo - 1

        historico_comparacion = df.copy()
        if id_sede_elegida is not None:
            historico_comparacion = historico_comparacion[
                pd.to_numeric(historico_comparacion["ID_SEDE"], errors="coerce")
                == id_sede_elegida
            ]

        ventas_por_periodo = historico_comparacion.groupby(
            ["ANIO", "MES_NUMERO"], as_index=False
        )["VENTAS_NETAS"].sum()
        valores_periodo = {
            (int(fila.ANIO), int(fila.MES_NUMERO)): float(fila.VENTAS_NETAS)
            for fila in ventas_por_periodo.itertuples(index=False)
        }
        valor_actual = valores_periodo.get((anio_actual, mes_actual))
        valor_anterior = valores_periodo.get(
            (periodo_anterior.year, periodo_anterior.month)
        )
        nombre_periodo_anterior = periodo_anterior.strftime("%b %Y")
        etiqueta_variacion = f"Variación vs {nombre_periodo_anterior}"

        if valor_actual is None:
            mensaje_variacion = "No hay ventas registradas para el periodo seleccionado."
        elif valor_anterior is None:
            mensaje_variacion = (
                f"No hay datos de {nombre_periodo_anterior} para calcular la variación."
            )
        else:
            variacion_mensual = valor_actual - valor_anterior
            porcentaje_variacion = (
                (variacion_mensual / valor_anterior * 100)
                if valor_anterior != 0
                else None
            )



def mostrar_grafico_monetario(
    datos_grafico,
    dimension,
    metrica,
    nombre_dimension,
    titulo,
    color,
    alto,
):
    datos_ordenados = datos_grafico.sort_values(metrica, ascending=False)
    grafico = (
        alt.Chart(datos_ordenados)
        .mark_bar(color=color)
        .encode(
            x=alt.X(
                f"{metrica}:Q",
                title="Monto (S/)",
                axis=alt.Axis(
                    format=",.0f",
                    labelExpr="'S/ ' + datum.label",
                ),
            ),
            y=alt.Y(
                f"{dimension}:N",
                title=None,
                sort=alt.SortField(field=metrica, order="descending"),
                axis=alt.Axis(labelLimit=220),
            ),
            tooltip=[
                alt.Tooltip(f"{dimension}:N", title=nombre_dimension),
                alt.Tooltip(f"{metrica}:Q", title="Monto (S/)", format=",.2f"),
            ],
        )
        .properties(height=alto, title=titulo)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            gridColor="#343A46",
            labelColor="#E6EAF0",
            titleColor="#E6EAF0",
            domainColor="#525866",
        )
        .configure_title(color="#F4F6F8", anchor="start", fontSize=14)
    )
    st.altair_chart(grafico, use_container_width=True)



tabs = st.tabs([
    "📊 Resumen",
    "🛒 Productos",
    "💳 Pagos",
    "📦 Compras",
    "🤖 Asistente IA",
])

with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas del resumen", f"{registros:,}")
    col2.metric("Número de ventas", f"{numero_ventas:,.0f}")
    col3.metric(
        "Ventas netas",
        f"S/ {ventas_netas / 1_000_000:.2f} M" if ventas_netas >= 1_000_000
        else f"S/ {ventas_netas:,.0f}",
        help=f"Importe exacto: S/ {ventas_netas:,.2f}",
    )
    col4.metric("Descuentos", f"S/ {descuentos:,.2f}")

    if etiqueta_variacion:
        if variacion_mensual is not None:
            porcentaje_texto = (
                f"{porcentaje_variacion:+.1f}%"
                if porcentaje_variacion is not None
                else "No calculable"
            )
            with st.container(border=True):
                col_variacion, col_contexto = st.columns([1, 3])
                col_variacion.metric(
                    etiqueta_variacion,
                    f"S/ {variacion_mensual:+,.2f}",
                    delta=porcentaje_texto,
                    help="Compara el mismo filtro de sede entre el periodo seleccionado y el mes anterior.",
                )
                col_contexto.markdown(
                    f"Ventas netas de **{periodo.strftime('%b %Y')}**: "
                    f"S/ {valor_actual:,.2f}  \n"
                    f"Ventas netas de **{periodo_anterior.strftime('%b %Y')}**: "
                    f"S/ {valor_anterior:,.2f}"
                )
        else:
            st.info(mensaje_variacion)
    else:
        st.caption(
            "Selecciona un año y un mes para ver la variación frente al mes anterior."
        )

    st.subheader("Ventas netas por mes")

    datos_grafico_mensual = datos.copy()
    mostrar_contexto_comparativo = False
    if anio_elegido != "Todos" and mes_elegido != "Todos":
        filas_periodo_actual = datos_periodo.loc[
            datos_periodo["MES"].astype(str) == mes_elegido,
            ["ANIO", "MES_NUMERO"],
        ].drop_duplicates()
        if not filas_periodo_actual.empty:
            periodo_seleccionado = pd.Period(
                year=int(anio_elegido),
                month=int(filas_periodo_actual.iloc[0]["MES_NUMERO"]),
                freq="M",
            )
            periodo_previo = periodo_seleccionado - 1
            periodos_grafico = {
                (periodo_seleccionado.year, periodo_seleccionado.month)
            }

            historico_grafico = df.copy()
            if id_sede_elegida is not None:
                historico_grafico = historico_grafico[
                    pd.to_numeric(historico_grafico["ID_SEDE"], errors="coerce")
                    == id_sede_elegida
                ]

            mascara_periodo_previo = (
                (historico_grafico["ANIO"] == periodo_previo.year)
                & (historico_grafico["MES_NUMERO"] == periodo_previo.month)
            )
            if mascara_periodo_previo.any():
                periodos_grafico.add(
                    (periodo_previo.year, periodo_previo.month)
                )
                mostrar_contexto_comparativo = True

            claves_periodo = (
                historico_grafico["ANIO"].astype(int) * 100
                + historico_grafico["MES_NUMERO"].astype(int)
            )
            claves_permitidas = {anio * 100 + mes for anio, mes in periodos_grafico}
            datos_grafico_mensual = historico_grafico[
                claves_periodo.isin(claves_permitidas)
            ].copy()

    ventas_mes = (
        datos_grafico_mensual.groupby(
            ["ANIO", "MES_NUMERO", "MES"], as_index=False
        )["VENTAS_NETAS"]
        .sum()
        .sort_values(["ANIO", "MES_NUMERO"])
    )

    ventas_mes["FECHA"] = pd.to_datetime(
        ventas_mes["ANIO"].astype(int).astype(str)
        + "-"
        + ventas_mes["MES_NUMERO"].astype(int).astype(str).str.zfill(2)
        + "-01"
    )
    ventas_mes["PERIODO"] = (
        ventas_mes["MES"].astype(str)
        + " "
        + ventas_mes["ANIO"].astype(int).astype(str)
    )
    ventas_mes["ORDEN_PERIODO"] = (
        ventas_mes["ANIO"].astype(int) * 100
        + ventas_mes["MES_NUMERO"].astype(int)
    )

    if not ventas_mes.empty:
        grafico_mensual = (
            alt.Chart(ventas_mes)
            .mark_bar(color="#83BD91")
            .encode(
                x=alt.X(
                    "PERIODO:N",
                    title="Mes",
                    sort=alt.SortField(field="ORDEN_PERIODO", order="ascending"),
                    axis=alt.Axis(labelAngle=-20, labelOverlap=False),
                ),
                y=alt.Y(
                    "VENTAS_NETAS:Q",
                    title="Ventas netas (S/)",
                    axis=alt.Axis(
                        format=",.0f",
                        labelExpr="'S/ ' + datum.label",
                    ),
                ),
                tooltip=[
                    alt.Tooltip("FECHA:T", title="Periodo", format="%b %Y"),
                    alt.Tooltip("VENTAS_NETAS:Q", title="Ventas netas (S/)", format=",.2f"),
                ],
            )
            .properties(height=310)
            .configure_view(strokeOpacity=0)
            .configure_axis(
                gridColor="#343A46",
                labelColor="#E6EAF0",
                titleColor="#E6EAF0",
                domainColor="#525866",
            )
        )
        st.altair_chart(grafico_mensual, use_container_width=True)
        if mostrar_contexto_comparativo:
            st.caption(
                "El gráfico muestra el periodo elegido y el mes anterior; "
                "las tablas conservan el filtro exacto seleccionado."
            )
    st.subheader("Datos del mart mensual")
    st.dataframe(datos, use_container_width=True)

with tabs[1]:
    st.subheader("🏆 Productos y categorías")
    if not datos_productos.empty:
        resumen_productos = (
            datos_productos.groupby("PRODUCTO", as_index=False)
            .agg(
                VENTAS_NETAS=("VENTAS_NETAS", "sum"),
                UNIDADES_VENDIDAS=("UNIDADES_VENDIDAS", "sum"),
            )
            .nlargest(10, "VENTAS_NETAS")
            .sort_values("VENTAS_NETAS", ascending=False)
        )
        resumen_categorias = (
            datos_productos.groupby("CATEGORIA", as_index=False)["VENTAS_NETAS"]
            .sum()
            .sort_values("VENTAS_NETAS", ascending=False)
        )

        col_productos, col_categorias = st.columns(2)
        with col_productos:
            mostrar_grafico_monetario(
                resumen_productos,
                "PRODUCTO",
                "VENTAS_NETAS",
                "Producto",
                "10 productos líderes",
                "#83BD91",
                360,
            )
        with col_categorias:
            mostrar_grafico_monetario(
                resumen_categorias,
                "CATEGORIA",
                "VENTAS_NETAS",
                "Categoría",
                "Ventas netas por categoría",
                "#E98982",
                300,
            )
        with st.expander("Ver detalle de productos"):
            st.dataframe(datos_productos, use_container_width=True)
    else:
        st.info(
            "Aún no está disponible el resumen de productos. "
            "Se generará en la próxima ejecución del orquestador."
        )

with tabs[2]:
    st.subheader("💳 Métodos de pago")
    if not datos_pagos.empty:
        resumen_pagos = (
            datos_pagos.groupby("METODO_PAGO", as_index=False)
            .agg(
                TOTAL_PAGADO=("TOTAL_PAGADO", "sum"),
                NUMERO_PAGOS=("NUMERO_PAGOS", "sum"),
            )
            .sort_values("TOTAL_PAGADO", ascending=False)
        )
        mostrar_grafico_monetario(
            resumen_pagos,
            "METODO_PAGO",
            "TOTAL_PAGADO",
            "Método de pago",
            "Importe pagado por método",
            "#6EA982",
            240,
        )
        with st.expander("Ver detalle de pagos"):
            st.dataframe(datos_pagos, use_container_width=True)
    else:
        st.info(
            "Aún no está disponible el resumen de pagos. "
            "Se generará en la próxima ejecución del orquestador."
        )

with tabs[3]:
    st.subheader("📦 Compras a proveedores")

    if not datos_compras.empty:
        total_comprado = datos_compras["TOTAL_COMPRADO"].sum()
        numero_compras = datos_compras["NUMERO_COMPRAS"].sum()
        unidades_compradas = datos_compras["UNIDADES_COMPRADAS"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Compras registradas", f"{numero_compras:,.0f}")
        col2.metric("Unidades compradas", f"{unidades_compradas:,.0f}")
        col3.metric("Monto comprado", f"S/ {total_comprado:,.2f}")

        resumen_proveedores = (
            datos_compras.groupby("PROVEEDOR", as_index=False)
            .agg(TOTAL_COMPRADO=("TOTAL_COMPRADO", "sum"))
            .sort_values("TOTAL_COMPRADO", ascending=False)
        )

        mostrar_grafico_monetario(
            resumen_proveedores,
            "PROVEEDOR",
            "TOTAL_COMPRADO",
            "Proveedor",
            "Monto comprado por proveedor",
            "#6EA982",
            300,
        )

        with st.expander("Ver detalle de compras"):
            st.dataframe(datos_compras, use_container_width=True)
    else:
        st.info(
            "Aún no está disponible el resumen de compras. "
            "Se generará cuando se ejecute el orquestador actualizado."
        )

with tabs[4]:
    st.divider()
    st.subheader("💬 Pregunta sobre tus ventas")

    if "historial_vivanda" not in st.session_state:
        st.session_state.historial_vivanda = []

    for mensaje in st.session_state.historial_vivanda:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

            if mensaje.get("sql"):
                with st.expander("Ver consulta SQL"):
                    st.code(mensaje["sql"], language="sql")

            if mensaje.get("filas") is not None:
                st.dataframe(
                    pd.DataFrame(mensaje["filas"]),
                    use_container_width=True,
                )

    st.caption("Prueba una pregunta rápida:")

    preguntas_rapidas = [
        ("🏆 Sede líder", "¿Qué sede tuvo más ventas netas?"),
        ("📍 Ventas por sede", "¿Cuánto vendió en ventas netas cada sede?"),
        ("📅 Mejor periodo", "¿Cuál fue el periodo completo (año y mes) con mayores ventas netas?"),
        ("💸 Total descuentos", "¿Cuál fue el total de descuentos?"),
    ]
    if "productos_filtrados" in tablas_permitidas:
        preguntas_rapidas.extend(
            [
                ("🛒 Top productos", "¿Qué 10 productos generaron más ventas netas?"),
                ("🧺 Ventas por categoría", "¿Cuánto vendió cada categoría?"),
            ]
        )
    if "pagos_filtrados" in tablas_permitidas:
        preguntas_rapidas.append(
            ("💳 Métodos de pago", "¿Cuánto se pagó por cada método de pago?")
        )
    
    if "compras_filtradas" in tablas_permitidas:
        preguntas_rapidas.extend(
            [
                ("🏭 Compras por proveedor", "¿Cuánto se compró a cada proveedor?"),
                ("📦 Compras por sede", "¿Cuánto se compró en cada sede?"),
                ("📅 Compras por mes", "¿Cuál fue el total comprado por mes?"),
            ]
        )

    columnas_preguntas = st.columns(2)
    pregunta_rapida = None

    for indice, (etiqueta, consulta) in enumerate(preguntas_rapidas):
        with columnas_preguntas[indice % 2]:
            if st.button(etiqueta, key=f"pregunta_rapida_{indice}"):
                pregunta_rapida = consulta

    with st.form("formulario_pregunta_vivanda", clear_on_submit=True):
        pregunta_escrita = st.text_input(
            "Escribe tu pregunta",
            placeholder="Ejemplo: ¿Qué sede tuvo más ventas netas?",
        )
        enviar_pregunta = st.form_submit_button("Consultar", type="primary")

    pregunta = pregunta_rapida or (pregunta_escrita if enviar_pregunta else None)
    if pregunta:
        st.session_state.historial_vivanda.append(
            {"role": "user", "content": pregunta}
        )

        with st.chat_message("user"):
            st.markdown(pregunta)

        tablas_y_columnas = [
            "ventas_filtradas: ANIO, MES_NUMERO, MES, ID_SEDE, SEDE, "
            "NUMERO_VENTAS, SUBTOTAL_VENTAS, DESCUENTOS, VENTAS_NETAS. "
            "Una fila por sede y mes."
        ]
        ejemplos_sql = []
        if "productos_filtrados" in tablas_permitidas:
            tablas_y_columnas.append(
                "productos_filtrados: ANIO, MES_NUMERO, MES, ID_SEDE, "
                "ID_PRODUCTO, SKU, PRODUCTO, ID_CATEGORIA, CATEGORIA, "
                "UNIDADES_VENDIDAS, SUBTOTAL_VENTAS, DESCUENTOS, "
                "VENTAS_NETAS, NUMERO_VENTAS. Una fila por producto, sede y mes."
            )
            ejemplos_sql.append(
                "Ejemplo de productos con mayor venta:\n"
                "SELECT PRODUCTO, SUM(VENTAS_NETAS) AS VENTAS_NETAS\n"
                "FROM productos_filtrados\n"
                "GROUP BY PRODUCTO\n"
                "ORDER BY VENTAS_NETAS DESC\n"
                "LIMIT 10\n\n"
                "Ejemplo de ventas por categoría:\n"
                "SELECT CATEGORIA, SUM(VENTAS_NETAS) AS VENTAS_NETAS\n"
                "FROM productos_filtrados\n"
                "GROUP BY CATEGORIA\n"
                "ORDER BY VENTAS_NETAS DESC"
            )
        if "pagos_filtrados" in tablas_permitidas:
            tablas_y_columnas.append(
                "pagos_filtrados: ANIO, MES_NUMERO, MES, ID_SEDE, "
                "ID_METODO_PAGO, METODO_PAGO, NUMERO_PAGOS, NUMERO_VENTAS, "
                "TOTAL_PAGADO. Una fila por método de pago, sede y mes."
            )
            ejemplos_sql.append(
                "Ejemplo de pagos por método:\n"
                "SELECT METODO_PAGO, SUM(TOTAL_PAGADO) AS TOTAL_PAGADO\n"
                "FROM pagos_filtrados\n"
                "GROUP BY METODO_PAGO\n"
                "ORDER BY TOTAL_PAGADO DESC"
            )
        
        if "compras_filtradas" in tablas_permitidas:
            tablas_y_columnas.append(
                "compras_filtradas: ANIO, MES_NUMERO, MES, ID_SEDE, SEDE, "
                "ID_ALMACEN, ALMACEN, ID_PROVEEDOR, PROVEEDOR, ESTADO_COMPRA, "
                "NUMERO_COMPRAS, UNIDADES_COMPRADAS, TOTAL_COMPRADO. "
                "Una fila por mes, sede, almacén, proveedor y estado."
            )
            ejemplos_sql.append(
                "Ejemplo de total comprado por proveedor:\\n"
                "SELECT PROVEEDOR, SUM(TOTAL_COMPRADO) AS TOTAL_COMPRADO\\n"
                "FROM compras_filtradas\\n"
                "GROUP BY PROVEEDOR\\n"
                "ORDER BY TOTAL_COMPRADO DESC"
            )

        sede_contexto = (
            "todas las sedes"
            if sede_elegida == "Todas"
            else sede_elegida
        )
        if anio_elegido != "Todos" and mes_elegido != "Todos":
            periodo_contexto = f"{mes_elegido} de {anio_elegido}"
        elif anio_elegido != "Todos":
            periodo_contexto = f"todos los meses de {anio_elegido}"
        elif mes_elegido != "Todos":
            periodo_contexto = f"{mes_elegido} de todos los años disponibles"
        else:
            periodo_contexto = "todos los periodos disponibles"

        contexto_respuesta = f"para {sede_contexto}, durante {periodo_contexto}"

        historial_previo = st.session_state.historial_vivanda[:-1]
        ultimas_preguntas = [
            mensaje.get("content", "").lower()
            for mensaje in reversed(historial_previo)
            if mensaje.get("role") == "user"
        ]
        pide_segundo_producto = bool(
            re.search(r"\b(segundo|segunda|2do|2da)\b", pregunta.lower())
            and ultimas_preguntas
            and "product" in ultimas_preguntas[0]
            and "productos_filtrados" in tablas_permitidas
        )
        
        pide_compras_anuladas = bool(
            "compras_filtradas" in tablas_permitidas
            and re.search(r"\b(anulad\w*|cancelad\w*)\b", pregunta.lower())
            and re.search(r"\b(compra\w*|pedido\w*)\b", pregunta.lower())
        )

        instrucciones = f"""
        Eres un asistente que analiza indicadores de ventas de Vivanda.
        Genera una sola consulta SQL válida para DuckDB y devuelve únicamente SQL,
        sin explicaciones ni bloques Markdown. La consulta debe comenzar con SELECT.
        Usa solo estas tablas locales disponibles: {", ".join(sorted(tablas_permitidas))}.
        Contexto de los filtros visibles: {sede_contexto}; {periodo_contexto}.
        Los datos locales ya tienen aplicados estos filtros. No agregues filtros
        adicionales por sede o periodo, salvo que la pregunta solicite una comparación.
        Usa el historial reciente para entender referencias como "¿y la segunda?";
        genera SQL solo para la pregunta actual y conserva el tema de seguimiento.
        Columnas y granularidad:
        {chr(10).join(tablas_y_columnas)}

        El filtro de sede ya se aplicó antes de consultar. No consultes archivos ni
        tablas fuera de la lista. Si los datos disponibles no responden la pregunta,
        responde exactamente: NO_SQL.

        Para comparar sedes por ventas netas, usa ventas_filtradas y suma VENTAS_NETAS
        agrupando por SEDE; ordena de mayor a menor. Si preguntan cuál sede lidera,
        devuelve solo la primera. Si piden los valores de todas las sedes, muéstralas todas.

        Para periodos, agrupa por ANIO, MES_NUMERO y MES. No agrupes solo por MES,
        porque mezclarías el mismo mes de años distintos.

        {("Para productos o categorías, usa productos_filtrados, suma VENTAS_NETAS y agrupa por PRODUCTO o CATEGORIA. Para unidades, suma UNIDADES_VENDIDAS." if "productos_filtrados" in tablas_permitidas else "")}
        {("Para pagos, usa pagos_filtrados y suma TOTAL_PAGADO por METODO_PAGO." if "pagos_filtrados" in tablas_permitidas else "")}
        {("Para compras, usa compras_filtradas. Suma TOTAL_COMPRADO para los montos y NUMERO_COMPRAS para contar compras. Agrupa por PROVEEDOR, SEDE, ALMACEN, ESTADO_COMPRA o por ANIO, MES_NUMERO y MES, según la pregunta." if "compras_filtradas" in tablas_permitidas else "")}
        {chr(10).join(ejemplos_sql)}
        """

        try:
            if pide_compras_anuladas:
                consulta = (
                    "SELECT COALESCE(SUM(NUMERO_COMPRAS), 0) "
                    "AS NUMERO_COMPRAS_ANULADAS "
                    "FROM compras_filtradas "
                    "WHERE UPPER(TRIM(ESTADO_COMPRA)) = 'ANULADA'" 
                )
            elif pide_segundo_producto:
                consulta = (
                    "SELECT PRODUCTO, SUM(VENTAS_NETAS) AS VENTAS_NETAS "
                    "FROM productos_filtrados GROUP BY PRODUCTO "
                    "ORDER BY VENTAS_NETAS DESC LIMIT 1 OFFSET 1"
                )
            else:
                historial_previo = [
                    mensaje
                    for mensaje in historial_previo
                    if mensaje.get("role") in {"user", "assistant"}
                ][-6:]
                mensajes_ollama = [{"role": "system", "content": instrucciones}]
                mensajes_ollama.extend(
                    {"role": mensaje["role"], "content": mensaje["content"]}
                    for mensaje in historial_previo
                )
                mensajes_ollama.append({"role": "user", "content": pregunta})

                respuesta_ollama = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "qwen2.5:3b",
                        "messages": mensajes_ollama,
                        "stream": False,
                        "options": {"temperature": 0},
                    },
                    timeout=180,
                )
                respuesta_ollama.raise_for_status()

                consulta = respuesta_ollama.json()["message"]["content"].strip()
                consulta = consulta.replace("```sql", "").replace("```", "").strip()
                consulta = re.sub(r"^sql\s*:\s*", "", consulta, flags=re.IGNORECASE)
                consulta = consulta.rstrip(";").strip()

            if consulta == "NO_SQL":
                texto = (
                    f"No puedo responder eso con los datos disponibles {contexto_respuesta}. "
                    "Puedo ayudarte con ventas, descuentos, sedes, periodos, "
                    "productos, categorías y métodos de pago."
                )
                filas = None
                consulta_segura = None
            else:
                if not re.match(r"^SELECT\b", consulta, flags=re.IGNORECASE):
                    raise ValueError("El modelo no generó una consulta SELECT.")

                if ";" in consulta or "--" in consulta or "/*" in consulta:
                    raise ValueError("La consulta contiene instrucciones no permitidas.")

                prohibidas = (
                    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|COPY|ATTACH|"
                    r"DETACH|PRAGMA|INSTALL|LOAD|EXPORT|IMPORT|READ_CSV|READ_PARQUET)\b"
                )
                if re.search(prohibidas, consulta, flags=re.IGNORECASE):
                    raise ValueError("Solo se permiten consultas de lectura.")

                tablas = re.findall(
                    r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w.]*)",
                    consulta,
                    flags=re.IGNORECASE,
                )

                tablas_no_permitidas = [
                    tabla
                    for tabla in tablas
                    if tabla.lower() not in tablas_permitidas
                ]
                if (
                    not tablas
                    or tablas_no_permitidas
                    or re.search(
                        r"\bFROM\s+[\w.]+(?:\s+(?:AS\s+)?[A-Za-z_]\w*)?\s*,",
                        consulta,
                        re.IGNORECASE,
                    )
                ):
                    raise ValueError(
                        "La consulta debe usar únicamente las tablas locales permitidas."
                    )

                resultado = conexion.execute(consulta).df()
                filas = resultado.to_dict(orient="records")
                consulta_segura = consulta
                if resultado.empty:
                    texto = (
                        f"No encontré resultados {contexto_respuesta}. "
                        "Prueba ampliando los filtros de sede, año o mes."
                    )
                elif resultado.shape == (1, 1):
                    nombre_columna = resultado.columns[0].upper()
                    valor = resultado.iloc[0, 0]
                    
                    if "NUMERO_COMPRAS_ANULADAS" in nombre_columna:
                        texto = (
                            f"Hay **{float(valor):,.0f} compras anuladas** "
                            f"{contexto_respuesta}."
                        )
                    elif "NUMERO_VENTAS" in nombre_columna:
                        texto = (
                            f"El resumen de {contexto_respuesta} registra "
                            f"**{float(valor):,.0f} ventas**."
                        )
                    elif "VENTAS_NETAS" in nombre_columna:
                        texto = (
                            f"Las ventas netas {contexto_respuesta} sumaron "
                            f"**S/ {float(valor):,.2f}**."
                        )
                    elif "DESCUENTOS" in nombre_columna:
                        texto = (
                            f"Los descuentos {contexto_respuesta} sumaron "
                            f"**S/ {float(valor):,.2f}**."
                        )
                    elif "TOTAL_PAGADO" in nombre_columna:
                        texto = (
                            f"El importe pagado {contexto_respuesta} fue de "
                            f"**S/ {float(valor):,.2f}**."
                        )
                    elif "UNIDADES_VENDIDAS" in nombre_columna:
                        texto = (
                            f"Se vendieron **{float(valor):,.0f} unidades** "
                            f"{contexto_respuesta}."
                        )
                    else:
                        texto = f"El resultado calculado es **{valor}**."
                    
                elif (
                    "ANIO" in resultado.columns
                    and "MES" in resultado.columns
                    and any(
                        "VENTAS_NETAS" in columna.upper()
                        for columna in resultado.columns
                    )
                ):
                    if len(resultado) > 1:
                        columna_ventas = next(
                            columna
                            for columna in resultado.columns
                            if "VENTAS_NETAS" in columna.upper()
                        )
                        resultado_ordenado = resultado.assign(
                            _VENTAS=pd.to_numeric(
                                resultado[columna_ventas], errors="coerce"
                            )
                        ).sort_values("_VENTAS", ascending=False)
                        fila = resultado_ordenado.iloc[0]
                        texto = (
                            f"El mejor periodo dentro de {contexto_respuesta} fue "
                            f"**{fila['MES']} {int(fila['ANIO'])}**, con "
                            f"**S/ {float(fila[columna_ventas]):,.2f}** en ventas netas. "
                            f"La tabla muestra {len(resultado)} periodos."
                        )
                    else:
                        fila = resultado.iloc[0]
                        columna_ventas = next(
                            columna
                            for columna in resultado.columns
                            if "VENTAS_NETAS" in columna.upper()
                        )
                        texto = (
                            f"El periodo con mayores ventas netas {contexto_respuesta} fue **{fila['MES']} {int(fila['ANIO'])}**, "
                            f"con **S/ {float(fila[columna_ventas]):,.2f}**."
                        )

                elif "SEDE" in resultado.columns and any(
                    "VENTAS_NETAS" in columna.upper()
                    for columna in resultado.columns
                ):
                    if len(resultado) > 1:
                        columna_ventas = next(
                            columna
                            for columna in resultado.columns
                            if "VENTAS_NETAS" in columna.upper()
                        )
                        resultado_ordenado = resultado.assign(
                            _VENTAS=pd.to_numeric(
                                resultado[columna_ventas], errors="coerce"
                            )
                        ).sort_values("_VENTAS", ascending=False)
                        fila = resultado_ordenado.iloc[0]
                        texto = (
                            f"La sede líder {contexto_respuesta} es "
                            f"**{fila['SEDE']}**, con **S/ "
                            f"{float(fila[columna_ventas]):,.2f}** en ventas netas. "
                            f"Te resumo las {len(resultado)} sedes en la tabla."
                        )
                    else:
                        fila = resultado.iloc[0]
                        columna_ventas = next(
                            columna
                            for columna in resultado.columns
                            if "VENTAS_NETAS" in columna.upper()
                        )
                        texto = (
                            f"El total acumulado de ventas netas de **{fila['SEDE']}** {contexto_respuesta} es "
                            f"**S/ {float(fila[columna_ventas]):,.2f}**."
                        )
                    
                elif (
                    "PRODUCTO" in resultado.columns
                    and any("VENTAS_NETAS" in columna.upper() for columna in resultado.columns)
                ):
                    columna_ventas = next(
                        columna
                        for columna in resultado.columns
                        if "VENTAS_NETAS" in columna.upper()
                    )
                    ventas_por_producto = pd.to_numeric(
                        resultado[columna_ventas], errors="coerce"
                    )
                    fila_lider = resultado.loc[ventas_por_producto.idxmax()]
                    top_productos = resultado.assign(
                        _VENTAS=ventas_por_producto
                    ).sort_values("_VENTAS", ascending=False).head(3)
                    destacados = "; ".join(
                        f"{fila['PRODUCTO']} (S/ {float(fila[columna_ventas]):,.2f})"
                        for _, fila in top_productos.iterrows()
                    )
                    if pide_segundo_producto:
                        texto = (
                            f"El segundo producto con mayores ventas netas "
                            f"{contexto_respuesta} fue **{fila_lider['PRODUCTO']}**, "
                            f"con **S/ {float(fila_lider[columna_ventas]):,.2f}**."
                        )
                    elif len(resultado) == 1:
                        texto = (
                            f"El producto líder {contexto_respuesta} fue "
                            f"**{fila_lider['PRODUCTO']}**, con "
                            f"**S/ {float(fila_lider[columna_ventas]):,.2f}**."
                        )
                    else:
                        texto = (
                            f"El producto líder {contexto_respuesta} fue "
                            f"**{fila_lider['PRODUCTO']}**, con "
                            f"**S/ {float(fila_lider[columna_ventas]):,.2f}**. "
                            f"Entre los siguientes puestos también aparecen: {destacados}."
                        )
                elif (
                    "CATEGORIA" in resultado.columns
                    and any("VENTAS_NETAS" in columna.upper() for columna in resultado.columns)
                ):
                    columna_ventas = next(
                        columna
                        for columna in resultado.columns
                        if "VENTAS_NETAS" in columna.upper()
                    )
                    ventas_por_categoria = pd.to_numeric(
                        resultado[columna_ventas], errors="coerce"
                    )
                    fila_lider = resultado.loc[ventas_por_categoria.idxmax()]
                    top_categorias = resultado.assign(
                        _VENTAS=ventas_por_categoria
                    ).sort_values("_VENTAS", ascending=False).head(3)
                    destacados = "; ".join(
                        f"{fila['CATEGORIA']} (S/ {float(fila[columna_ventas]):,.2f})"
                        for _, fila in top_categorias.iterrows()
                    )
                    texto = (
                        f"La categoría líder {contexto_respuesta} fue "
                        f"**{fila_lider['CATEGORIA']}**, con "
                        f"**S/ {float(fila_lider[columna_ventas]):,.2f}**. "
                        f"El top disponible es: {destacados}."
                    )
                elif (
                    "METODO_PAGO" in resultado.columns
                    and any("TOTAL_PAGADO" in columna.upper() for columna in resultado.columns)
                ):
                    columna_total = next(
                        columna
                        for columna in resultado.columns
                        if "TOTAL_PAGADO" in columna.upper()
                    )
                    pagos_por_metodo = pd.to_numeric(
                        resultado[columna_total], errors="coerce"
                    )
                    fila_lider = resultado.loc[pagos_por_metodo.idxmax()]
                    top_metodos = resultado.assign(
                        _PAGADO=pagos_por_metodo
                    ).sort_values("_PAGADO", ascending=False).head(3)
                    destacados = "; ".join(
                        f"{fila['METODO_PAGO']} (S/ {float(fila[columna_total]):,.2f})"
                        for _, fila in top_metodos.iterrows()
                    )
                    texto = (
                        f"El método más utilizado por importe {contexto_respuesta} fue "
                        f"**{fila_lider['METODO_PAGO']}**, con "
                        f"**S/ {float(fila_lider[columna_total]):,.2f}**. "
                        f"El top disponible es: {destacados}."
                    )
                elif (
                    "TOTAL_COMPRADO" in resultado.columns
                    and (
                        "PROVEEDOR" in resultado.columns
                        or "SEDE" in resultado.columns
                    )
                ):
                    dimension = (
                        "PROVEEDOR"
                        if "PROVEEDOR" in resultado.columns
                        else "SEDE"
                    )
                    ranking = resultado.assign(
                        _MONTO=pd.to_numeric(
                            resultado["TOTAL_COMPRADO"], errors="coerce"
                        )
                    ).dropna(subset=["_MONTO"]).sort_values(
                        "_MONTO", ascending=False
                    )

                    if not ranking.empty:
                        lider = ranking.iloc[0]
                        entidad = (
                            "El proveedor"
                            if dimension == "PROVEEDOR"
                            else "La sede"
                        )
                        texto = (
                            f"{entidad} con mayor monto de compras "
                            f"{contexto_respuesta} fue **{lider[dimension]}**, "
                            f"con **S/ {float(lider['_MONTO']):,.2f}**. "
                            f"La tabla muestra los {len(ranking)} resultados."
                        )
                    else:
                        texto = (
                            f"No pude interpretar los montos de compras "
                            f"{contexto_respuesta}."
                        )
                elif len(resultado.columns) == 1:
                    nombre_columna = resultado.columns[0].replace("_", " ").lower()
                    valores = resultado.iloc[:, 0].dropna().astype(str).tolist()
                    muestra = ", ".join(valores[:5])
                    sufijo = "…" if len(valores) > 5 else ""
                    texto = (
                        f"Encontré {len(valores)} valores de {nombre_columna} "
                        f"{contexto_respuesta}: {muestra}{sufijo}."
                    )
                else:
                    texto = (
                        f"Consulta completada {contexto_respuesta}. "
                        f"Encontré {len(resultado)} resultado(s). "
                        "Revisa la tabla para ver el detalle."
                    )
            with st.chat_message("assistant"):
                st.markdown(texto)

                if consulta_segura:
                    with st.expander("Ver consulta SQL"):
                        st.code(consulta_segura, language="sql")

                if filas is not None:
                    st.dataframe(pd.DataFrame(filas), use_container_width=True)

            st.session_state.historial_vivanda.append(
                {
                    "role": "assistant",
                    "content": texto,
                    "sql": consulta_segura,
                    "filas": filas,
                }
            )

        except requests.exceptions.ConnectionError:
            texto = (
                "No encuentro Ollama activo. Abre Ollama y vuelve a enviar "
                "la pregunta."
            )
            st.session_state.historial_vivanda.append(
                {"role": "assistant", "content": texto}
            )
            with st.chat_message("assistant"):
                st.markdown(texto)

        except Exception as error:
            texto = f"No pude procesar la pregunta: {error}"
            st.session_state.historial_vivanda.append(
                {"role": "assistant", "content": texto}
            )
            with st.chat_message("assistant"):
                st.markdown(texto)
conexion.close()
