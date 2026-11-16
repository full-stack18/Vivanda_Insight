{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_producto') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_producto"
    ORDER BY "id_producto"
) = 1