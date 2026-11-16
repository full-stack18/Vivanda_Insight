{{ config(materialized='table') }}

SELECT
    d.id_detalle,
    d.id_venta,
    d.id_producto,
    v."id_sede" AS id_sede,
    v."id_empleado" AS id_empleado,
    v."id_cliente" AS id_cliente,
    f.fecha_key,
    CAST(v."fecha" AS DATE) AS fecha_venta,
    v."estado" AS estado_venta,
    d.cantidad,
    d.precio_unitario,
    d.descuento,
    d.total_linea
FROM {{ ref('int_detalle_venta') }} AS d
JOIN {{ ref('stg_venta') }} AS v
    ON d.id_venta = v."id_venta"
LEFT JOIN {{ ref('dim_fecha') }} AS f
    ON CAST(v."fecha" AS DATE) = f.fecha