{{ config(materialized='table') }}

SELECT
    m."id_movimiento" AS id_movimiento,
    m."id_almacen" AS id_almacen,
    m."id_producto" AS id_producto,
    m."id_empleado" AS id_empleado,
    f.fecha_key,
    CAST(m."fecha" AS TIMESTAMP_NTZ) AS fecha_movimiento,
    UPPER(TRIM(m."tipo")) AS tipo_movimiento,
    CAST(m."cantidad" AS NUMBER(18, 3)) AS cantidad,
    CASE
        WHEN UPPER(TRIM(m."tipo")) = 'SALIDA'
            THEN -ABS(CAST(m."cantidad" AS NUMBER(18, 3)))
        ELSE ABS(CAST(m."cantidad" AS NUMBER(18, 3)))
    END AS cantidad_neta,
    NULLIF(TRIM(m."observacion"), '') AS observacion
FROM {{ ref('stg_movimiento_inventario') }} AS m
LEFT JOIN {{ ref('dim_fecha') }} AS f
    ON CAST(m."fecha" AS DATE) = f.fecha