{{ config(materialized='table') }}

SELECT
    i."id_inventario" AS id_inventario,
    p."id_producto" AS id_producto,
    p."sku" AS sku,
    p."nombre" AS producto,
    c."id_categoria" AS id_categoria,
    c."nombre" AS categoria,
    a."id_almacen" AS id_almacen,
    a."nombre" AS almacen,
    a."id_sede" AS id_sede,
    s.nombre AS sede,
    CAST(i."stock_actual" AS NUMBER(18, 3)) AS stock_actual,
    CAST(i."stock_minimo" AS NUMBER(18, 3)) AS stock_minimo,
    CASE
        WHEN i."stock_actual" <= i."stock_minimo" THEN 'REPOSICION'
        ELSE 'DISPONIBLE'
    END AS estado_stock,
    CAST(i."actualizado_en" AS TIMESTAMP_NTZ) AS actualizado_en
FROM {{ ref('stg_inventario') }} AS i
JOIN {{ ref('dim_producto') }} AS p
    ON i."id_producto" = p."id_producto"
JOIN {{ ref('dim_almacen') }} AS a
    ON i."id_almacen" = a."id_almacen"
LEFT JOIN {{ ref('dim_sede') }} AS s
    ON a."id_sede" = s.id_sede
LEFT JOIN {{ ref('dim_categoria') }} AS c
    ON p."id_categoria" = c."id_categoria"
