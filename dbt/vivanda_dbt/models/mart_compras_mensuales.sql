{{ config(materialized='table') }}

SELECT
    d.anio,
    d.mes_numero,
    INITCAP(TO_CHAR(d.fecha, 'MON')) AS mes,
    f.id_sede,
    s.nombre AS sede,
    f.id_almacen,
    a."nombre" AS almacen,
    f.id_proveedor,
    p.razon_social AS proveedor,
    f.estado_compra,
    COUNT(DISTINCT f.id_compra) AS numero_compras,
    SUM(f.cantidad) AS unidades_compradas,
    SUM(f.total_linea) AS total_comprado
FROM {{ ref('fact_compra') }} AS f
JOIN {{ ref('dim_fecha') }} AS d
    ON f.fecha_key = d.fecha_key
LEFT JOIN {{ ref('dim_sede') }} AS s
    ON f.id_sede = s.id_sede
LEFT JOIN {{ ref('dim_almacen') }} AS a
    ON f.id_almacen = a."id_almacen"
LEFT JOIN {{ ref('dim_proveedor') }} AS p
    ON f.id_proveedor = p.id_proveedor
GROUP BY
    d.anio,
    d.mes_numero,
    INITCAP(TO_CHAR(d.fecha, 'MON')),
    f.id_sede,
    s.nombre,
    f.id_almacen,
    a."nombre",
    f.id_proveedor,
    p.razon_social,
    f.estado_compra