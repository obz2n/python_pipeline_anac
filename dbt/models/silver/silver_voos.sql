{{ config(materialized = 'table') }}

-- silver_voos (MariaDB-compatible)
-- Camada Silver: limpeza, tipagem e enriquecimento dos voos da ANAC.
-- Usa dt_referencia como data de base para decomposição temporal.
-- Dados enriquecidos com informações geográficas via seed_aeroportos.

select
  b.sg_empresa_icao,
  b.nr_voo,
  b.nr_singular,
  b.id_di,
  b.cd_di,
  b.id_tipo_linha,
  b.cd_tipo_linha,
  b.sg_icao_origem,
  b.sg_icao_destino,
  b.dt_referencia,
  b.dt_partida_real,
  b.hr_partida_real,
  b.dt_chegada_real,
  b.hr_chegada_real,
  b.nr_passag_pagos,
  b.nr_passag_gratis,
  b.kg_carga_paga,
  b.kg_carga_gratis,
  b.km_distancia,

  -- Decomposição de data baseada em dt_referencia (data prevista de início)
  b.dt_referencia_ts,
  YEAR(b.dt_referencia_ts) as ano,
  MONTH(b.dt_referencia_ts) as mes,
  DAY(b.dt_referencia_ts) as dia,
  QUARTER(b.dt_referencia_ts) as trimestre,
  (WEEKDAY(b.dt_referencia_ts) + 1) as dia_semana_num,
  DATE_FORMAT(b.dt_referencia_ts, '%M') as nome_mes,
  DATE_FORMAT(b.dt_referencia_ts, '%W') as nome_dia_semana,

  -- Flag de situação baseado em disponibilidade de datas reais
  case
    when b.dt_chegada_real is not null then 'realizado'
    when b.dt_partida_real is not null then 'em_voo'
    else 'programado'
  end as flag_situacao,

  -- Enriquecimento geográfico: origem
  origem.cidade as origem_cidade,
  origem.estado as origem_estado,
  origem.uf as origem_uf,
  origem.regiao as origem_regiao,

  -- Enriquecimento geográfico: destino
  destino.cidade as destino_cidade,
  destino.estado as destino_estado,
  destino.uf as destino_uf,
  destino.regiao as destino_regiao,

  -- Rota concatenada
  CONCAT(b.sg_icao_origem, ' -> ', b.sg_icao_destino) as rota,

  -- Metadata
  b.source_file

from (
  select
    t.*,
    case
      when t.dt_referencia REGEXP '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
        then STR_TO_DATE(t.dt_referencia, '%d/%m/%Y')
    end as dt_referencia_ts
  from {{ source('bronze', 'bronze_anac') }} as t
) as b

left join {{ ref('bronze_seed_aeroportos') }} as origem
  on b.sg_icao_origem = origem.icao_aerodromo
left join {{ ref('bronze_seed_aeroportos') }} as destino
  on b.sg_icao_destino = destino.icao_aerodromo
