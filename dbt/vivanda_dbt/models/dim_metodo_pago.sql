{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_metodo_pago') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_metodo_pago"
    ORDER BY "id_metodo_pago"
) = 1