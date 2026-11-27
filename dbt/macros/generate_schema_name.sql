{#- Usa o schema configurado (staging/marts) como sufixo do dataset do target:
    radar_dev_staging, radar_dev_marts, radar_staging, radar_marts. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
