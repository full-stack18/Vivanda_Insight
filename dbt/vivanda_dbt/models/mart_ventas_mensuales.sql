{{ config(materialized='table') }}

SELECT
    d.anio,
    d.mes_numero,
    d.mes,
    f.id_sede,
    s.nombre AS sede,
    COUNT(DISTINCT f.id_venta) AS numero_ventas,
    SUM(f.subtotal) AS subtotal_ventas,
    SUM(f.descuento) AS descuentos,
    SUM(f.total) AS ventas_netas
FROM {{ ref('fact_venta') }} AS f
JOIN {{ ref('dim_fecha') }} AS d
    ON f.fecha_key = d.fecha_key
LEFT JOIN {{ ref('dim_sede') }} AS s
    ON f.id_sede = s.id_sede
GROUP BY
    d.anio,
    d.mes_numero,
    d.mes,
    f.id_sede,
    s.nombre