{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_cliente') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_cliente"
    ORDER BY "id_cliente"
) = 1