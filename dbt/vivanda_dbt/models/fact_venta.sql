{{ config(materialized='table') }}

SELECT
    v."id_venta" AS id_venta,
    v."id_sede" AS id_sede,
    v."id_empleado" AS id_empleado,
    v."id_cliente" AS id_cliente,
    f.fecha_key,
    CAST(v."fecha" AS DATE) AS fecha_venta,
    v."estado" AS estado_venta,
    v."subtotal" AS subtotal,
    v."descuento" AS descuento,
    v."total" AS total
FROM {{ ref('stg_venta') }} AS v
LEFT JOIN {{ ref('dim_fecha') }} AS f
    ON CAST(v."fecha" AS DATE) = f.fecha