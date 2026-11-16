{{ config(materialized='table') }}

SELECT
    p."id_pago" AS id_pago,
    p."id_venta" AS id_venta,
    p."id_metodo_pago" AS id_metodo_pago,
    f.fecha_key,
    CAST(p."fecha" AS TIMESTAMP_NTZ) AS fecha_pago,
    CAST(p."monto" AS NUMBER(18, 2)) AS monto,
    NULLIF(TRIM(p."referencia"), '') AS referencia
FROM {{ ref('stg_pago') }} AS p
LEFT JOIN {{ ref('dim_fecha') }} AS f
    ON CAST(p."fecha" AS DATE) = f.fecha