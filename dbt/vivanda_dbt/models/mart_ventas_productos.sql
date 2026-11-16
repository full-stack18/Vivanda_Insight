{{ config(materialized='table') }}

SELECT
    YEAR(f.fecha_venta) AS anio,
    MONTH(f.fecha_venta) AS mes_numero,
    INITCAP(TO_CHAR(f.fecha_venta, 'MON')) AS mes,
    f.id_sede,
    p."id_producto" AS id_producto,
    p."sku" AS sku,
    p."nombre" AS producto,
    c."id_categoria" AS id_categoria,
    c."nombre" AS categoria,
    SUM(f.cantidad) AS unidades_vendidas,
    SUM(f.cantidad * f.precio_unitario) AS subtotal_ventas,
    SUM(f.descuento) AS descuentos,
    SUM(f.total_linea) AS ventas_netas,
    COUNT(DISTINCT f.id_venta) AS numero_ventas
FROM {{ ref('fact_detalle_venta') }} AS f
JOIN {{ ref('dim_producto') }} AS p
    ON f.id_producto = p."id_producto"
LEFT JOIN {{ ref('dim_categoria') }} AS c
    ON p."id_categoria" = c."id_categoria"
GROUP BY
    YEAR(f.fecha_venta),
    MONTH(f.fecha_venta),
    INITCAP(TO_CHAR(f.fecha_venta, 'MON')),
    f.id_sede,
    p."id_producto",
    p."sku",
    p."nombre",
    c."id_categoria",
    c."nombre"
