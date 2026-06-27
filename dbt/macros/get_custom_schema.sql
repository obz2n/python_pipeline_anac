{% macro generate_schema_name(custom_schema_name, node) -%}
    {#-
        Por padrão, o dbt concatena target_schema + custom_schema (ex: raw_silver).
        Aqui sobrescrevemos para usar o schema customizado puro (ex: silver, gold).
    -#}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
