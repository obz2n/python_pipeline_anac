-- dbt/models/bronze/bronze_anac.sql
{{ config(materialized='view') }}

-- Expor os dados brutos da tabela raw.raw_anac (source name: 'raw')
select *
from {{ source('raw', 'raw_anac') }}
