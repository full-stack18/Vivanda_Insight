{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_categoria') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_categoria"
    ORDER BY "id_categoria"
) = 1