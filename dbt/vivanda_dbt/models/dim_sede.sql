{{ config(materialized='table') }}

SELECT DISTINCT
    "id_sede" AS id_sede,
    NULLIF(TRIM("codigo"), '') AS codigo,
    NULLIF(TRIM("nombre"), '') AS nombre,
    NULLIF(TRIM("departamento"), '') AS departamento,
    NULLIF(TRIM("provincia"), '') AS provincia,
    NULLIF(TRIM("distrito"), '') AS distrito,
    "activo" AS activo
FROM {{ ref('stg_sede') }}