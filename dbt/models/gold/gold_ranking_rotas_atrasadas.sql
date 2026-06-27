{{
  config(
    materialized = 'table'
  )
}}

-- gold_ranking_rotas_atrasadas (MariaDB-compatible)
-- Ranking das rotas por volume de voos em progresso (saiu mas não chegou).
-- Filtra rotas com volume mínimo para evitar outliers de rotas pouco operadas.

{% set volume_minimo = 30 %}

with silver as (

    select * from {{ ref('silver_voos') }}
    where flag_situacao in ('realizado', 'em_voo')   -- exclui programados

),

agregado_rota as (

    select
        rota,
        icao_aerodromo_origem,
        origem_cidade,
        origem_uf,
        icao_aerodromo_destino,
        destino_cidade,
        destino_uf,

        count(*) as total_voos,
        SUM(CASE WHEN flag_situacao = 'em_voo' THEN 1 ELSE 0 END) as voos_em_voo,
        SUM(CASE WHEN flag_situacao = 'realizado' THEN 1 ELSE 0 END) as voos_realizados

    from silver
    group by
        rota, icao_aerodromo_origem, origem_cidade, origem_uf,
        icao_aerodromo_destino, destino_cidade, destino_uf

    having count(*) >= {{ volume_minimo }}   -- ignora rotas com poucos voos

)

select
    *,

    round(100.0 * voos_em_voo / nullif(total_voos, 0), 1) as taxa_em_voo_pct,

    rank() over (order by voos_em_voo desc) as ranking_volume_em_voo

from agregado_rota
order by ranking_volume_em_voo
