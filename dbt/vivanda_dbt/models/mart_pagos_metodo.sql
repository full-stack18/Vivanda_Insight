{{ config(materialized='table') }}

SELECT
    YEAR(p.fecha_pago) AS anio,
    MONTH(p.fecha_pago) AS mes_numero,
    INITCAP(TO_CHAR(p.fecha_pago, 'MON')) AS mes,
    v.id_sede,
    m."id_metodo_pago" AS id_metodo_pago,
    m."nombre" AS metodo_pago,
    COUNT(DISTINCT p.id_pago) AS numero_pagos,
    COUNT(DISTINCT p.id_venta) AS numero_ventas,
    SUM(p.monto) AS total_pagado
FROM {{ ref('fact_pago') }} AS p
JOIN {{ ref('fact_venta') }} AS v
    ON p.id_venta = v.id_venta
JOIN {{ ref('dim_metodo_pago') }} AS m
    ON p.id_metodo_pago = m."id_metodo_pago"
GROUP BY
    YEAR(p.fecha_pago),
    MONTH(p.fecha_pago),
    INITCAP(TO_CHAR(p.fecha_pago, 'MON')),
    v.id_sede,
    m."id_metodo_pago",
    m."nombre"
