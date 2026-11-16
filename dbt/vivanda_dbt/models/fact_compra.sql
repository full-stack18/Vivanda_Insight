{{ config(materialized='table') }}

SELECT
    c."id_compra" AS id_compra,
    d."id_detalle" AS id_detalle,
    c."id_sede" AS id_sede,
    c."id_almacen" AS id_almacen,
    c."id_proveedor" AS id_proveedor,
    c."id_empleado" AS id_empleado,
    d."id_producto" AS id_producto,
    f.fecha_key,
    CAST(c."fecha" AS TIMESTAMP_NTZ) AS fecha_compra,
    UPPER(TRIM(c."estado")) AS estado_compra,
    CAST(d."cantidad" AS NUMBER(18, 3)) AS cantidad,
    CAST(d."costo_unitario" AS NUMBER(18, 4)) AS costo_unitario,
    CAST(d."cantidad" AS NUMBER(18, 3))
        * CAST(d."costo_unitario" AS NUMBER(18, 4)) AS total_linea
FROM {{ ref('stg_compra') }} AS c
JOIN {{ ref('stg_detalle_compra') }} AS d
    ON c."id_compra" = d."id_compra"
LEFT JOIN {{ ref('dim_fecha') }} AS f
    ON CAST(c."fecha" AS DATE) = f.fecha