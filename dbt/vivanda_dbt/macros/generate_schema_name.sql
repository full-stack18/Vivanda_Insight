{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set model_name = node.name | lower -%}
    {%- if model_name.startswith('stg_') or model_name.startswith('int_') or model_name.startswith('snap_') -%}
        SILVER
    {%- elif model_name.startswith('dim_') or model_name.startswith('fact_') or model_name.startswith('mart_') -%}
        GOLD
    {%- elif custom_schema_name is not none -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}
{%- endmacro %}