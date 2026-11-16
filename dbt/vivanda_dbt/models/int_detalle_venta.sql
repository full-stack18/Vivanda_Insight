{{ config(materialized='view') }}

WITH detalle AS (
    SELECT
        "id_detalle" AS id_detalle,
        "id_venta" AS id_venta,
        "id_producto" AS id_producto,
        CAST("cantidad" AS NUMBER(18, 0)) AS cantidad,
        CAST("precio_unitario" AS NUMBER(18, 2)) AS precio_unitario,
        COALESCE(CAST("descuento" AS NUMBER(18, 2)), 0) AS descuento
    FROM {{ ref('stg_detalle_venta') }}
)

SELECT
    id_detalle,
    id_venta,
    id_producto,
    cantidad,
    precio_unitario,
    descuento,
    CAST(cantidad * precio_unitario - descuento AS NUMBER(18, 2)) AS total_linea
FROM detalle