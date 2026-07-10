{{ config(materialized = 'table') }}

-- silver_voos (PostgreSQL-compatible)
-- Camada Silver: limpeza, tipagem e enriquecimento dos voos da ANAC.
-- Usa dt_referencia como data de base para decomposição temporal.
-- Dados enriquecidos com informações geográficas via seed_aeroportos.

with src as (
  -- Referência direta à tabela bronze, selecionando apenas colunas existentes
  select
    *
  from {{ source('bronze', 'bronze_anac') }}
),

datas_processadas as (
  -- Processa datas de referência em formato DD/MM/YYYY
  select
    src.*,
    -- Converter dt_referencia para timestamp
    case
      when src.dt_referencia ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
        then to_date(src.dt_referencia, 'DD/MM/YYYY')
      else null
    end as dt_referencia_ts
  from src
),

temporal_decomposition as (
  -- Decomposição temporal baseada em dt_referencia
  select
    datas_processadas.*,
    extract(year from datas_processadas.dt_referencia_ts)::int as ano,
    extract(month from datas_processadas.dt_referencia_ts)::int as mes,
    extract(day from datas_processadas.dt_referencia_ts)::int as dia,
    extract(quarter from datas_processadas.dt_referencia_ts)::int as trimestre,
    extract(dow from datas_processadas.dt_referencia_ts)::int as dia_semana_num,
    to_char(datas_processadas.dt_referencia_ts, 'Month') as nome_mes,
    to_char(datas_processadas.dt_referencia_ts, 'Day') as nome_dia_semana
  from datas_processadas
),

situacao_voo as (
  -- Flag de situação baseado em disponibilidade de datas reais
  select
    temporal_decomposition.*,
    case
      when temporal_decomposition.dt_chegada_real is not null then 'realizado'
      when temporal_decomposition.dt_partida_real is not null then 'em_voo'
      else 'programado'
    end as flag_situacao,
    temporal_decomposition.sg_icao_origem || ' -> ' || temporal_decomposition.sg_icao_destino as rota
  from temporal_decomposition
)

select
  situacao_voo.id_combinada,
  situacao_voo.id_empresa,
  situacao_voo.sg_empresa_icao,
  situacao_voo.sg_empresa_iata,
  situacao_voo.nm_empresa,
  situacao_voo.nm_pais,
  situacao_voo.ds_tipo_empresa,
  situacao_voo.nr_voo,
  situacao_voo.nr_singular,
  situacao_voo.id_di,
  situacao_voo.cd_di,
  situacao_voo.ds_di,
  situacao_voo.ds_grupo_di,
  situacao_voo.id_tipo_linha,
  situacao_voo.cd_tipo_linha,
  situacao_voo.ds_tipo_linha,
  situacao_voo.ds_natureza_tipo_linha,
  situacao_voo.ds_servico_tipo_linha,
  situacao_voo.ds_natureza_etapa,
  situacao_voo.dt_referencia,
  situacao_voo.dt_referencia_ts,
  situacao_voo.ano,
  situacao_voo.mes,
  situacao_voo.dia,
  situacao_voo.trimestre,
  situacao_voo.dia_semana_num,
  situacao_voo.nome_mes,
  situacao_voo.nome_dia_semana,
  situacao_voo.hr_partida_real,
  situacao_voo.dt_partida_real,
  situacao_voo.hr_chegada_real,
  situacao_voo.dt_chegada_real,
  situacao_voo.sg_icao_origem,
  situacao_voo.sg_iata_origem,
  situacao_voo.nm_aerodromo_origem,
  situacao_voo.nm_municipio_origem,
  situacao_voo.sg_uf_origem,
  situacao_voo.nm_regiao_origem,
  situacao_voo.nm_pais_origem,
  situacao_voo.nm_continente_origem,
  situacao_voo.nr_etapa,
  situacao_voo.sg_icao_destino,
  situacao_voo.sg_iata_destino,
  situacao_voo.nm_aerodromo_destino,
  situacao_voo.nm_municipio_destino,
  situacao_voo.sg_uf_destino,
  situacao_voo.nm_regiao_destino,
  situacao_voo.nm_pais_destino,
  situacao_voo.nm_continente_destino,
  situacao_voo.nr_escala_destino,
  situacao_voo.nr_passag_pagos,
  situacao_voo.nr_passag_gratis,
  situacao_voo.kg_bagagem_livre,
  situacao_voo.kg_bagagem_excesso,
  situacao_voo.kg_carga_paga,
  situacao_voo.kg_carga_gratis,
  situacao_voo.kg_correio,
  situacao_voo.flag_situacao,
  situacao_voo.rota,
  -- Enriquecimento geográfico (left join tolera ausência de dados)
  origem.nome_aeroporto as origem_nome_aeroporto,
  origem.cidade as origem_cidade,
  origem.estado as origem_estado,
  origem.uf as origem_uf_seed,
  origem.regiao as origem_regiao_seed,
  destino.nome_aeroporto as destino_nome_aeroporto,
  destino.cidade as destino_cidade,
  destino.estado as destino_estado,
  destino.uf as destino_uf_seed,
  destino.regiao as destino_regiao_seed,
  situacao_voo.source_file

from situacao_voo

-- Joins com seed de aeroportos (left join tolera falta de dados)
left join {{ ref('bronze_seed_aeroportos') }} as origem
  on situacao_voo.sg_icao_origem = origem.icao_aerodromo
left join {{ ref('bronze_seed_aeroportos') }} as destino
  on situacao_voo.sg_icao_destino = destino.icao_aerodromo
