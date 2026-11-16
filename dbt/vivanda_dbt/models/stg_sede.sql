{{ config(materialized='view') }}

SELECT *
FROM {{ source('vivanda_bronze', 'SEDE') }}