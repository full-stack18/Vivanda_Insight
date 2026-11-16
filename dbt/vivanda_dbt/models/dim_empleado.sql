{{ config(materialized='table') }}

SELECT *
FROM {{ ref('stg_empleado') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY "id_empleado"
    ORDER BY "id_empleado"
) = 1