{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_almacen') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_almacen"
    ORDER BY "id_almacen"
) = 1