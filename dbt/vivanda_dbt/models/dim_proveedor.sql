{{ config(materialized='table') }}

SELECT
    "id_proveedor" AS id_proveedor,
    NULLIF(TRIM("ruc"), '') AS ruc,
    NULLIF(TRIM("razon_social"), '') AS razon_social,
    TO_VARCHAR("telefono") AS telefono,
    NULLIF(TRIM("correo"), '') AS correo,
    "activo" AS activo
FROM {{ ref('stg_proveedor') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_proveedor"
    ORDER BY "id_proveedor"
) = 1