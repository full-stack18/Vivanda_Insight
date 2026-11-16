{{ config(materialized='table') }}

WITH fechas AS (
    SELECT CAST("fecha" AS DATE) AS fecha
    FROM {{ ref('stg_venta') }}
    WHERE "fecha" IS NOT NULL

    UNION

    SELECT CAST("fecha" AS DATE)
    FROM {{ ref('stg_pago') }}
    WHERE "fecha" IS NOT NULL

    UNION

    SELECT CAST("fecha" AS DATE)
    FROM {{ ref('stg_movimiento_inventario') }}
    WHERE "fecha" IS NOT NULL

    UNION

    SELECT CAST("fecha" AS DATE)
    FROM {{ ref('stg_compra') }}
    WHERE "fecha" IS NOT NULL
)

SELECT
    TO_NUMBER(TO_CHAR(fecha, 'YYYYMMDD')) AS fecha_key,
    fecha,
    YEAR(fecha) AS anio,
    QUARTER(fecha) AS trimestre,
    MONTH(fecha) AS mes_numero,
    MONTHNAME(fecha) AS mes,
    DAY(fecha) AS dia,
    DAYOFWEEKISO(fecha) AS dia_semana_numero,
    DAYNAME(fecha) AS dia_semana
FROM fechas