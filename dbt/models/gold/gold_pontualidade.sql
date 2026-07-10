-- gold_pontualidade (PostgreSQL-compatible)
-- Métricas de realização agregadas por empresa, rota, aeroporto e período.
-- Wide table: cada linha traz todos os atributos necessários para BI,
-- sem necessidade de joins adicionais.

with silver as (

    select * from {{ ref('silver_voos') }}
    where flag_situacao is not null   -- ignora linhas totalmente vazias

),

agregado as (

    select
        sg_empresa_icao,
        sg_icao_origem,
        origem_cidade,
        origem_estado,
        nm_regiao_origem,
        sg_icao_destino,
        destino_cidade,
        destino_estado,
        nm_regiao_destino,
        rota,
        ano,
        mes,

        count(*) as total_voos,
        SUM(CASE WHEN flag_situacao = 'realizado' THEN 1 ELSE 0 END) as voos_realizados,
        SUM(CASE WHEN flag_situacao = 'em_voo' THEN 1 ELSE 0 END) as voos_em_voo,
        SUM(CASE WHEN flag_situacao = 'programado' THEN 1 ELSE 0 END) as voos_programados

    from silver
    group by
        sg_empresa_icao, sg_icao_origem, origem_cidade, origem_estado, nm_regiao_origem,
        sg_icao_destino, destino_cidade, destino_estado, nm_regiao_destino,
        rota, ano, mes

)

select
    *,

    -- Taxa de realização: voos realizados sobre total
    round(
        100.0 * voos_realizados / nullif(total_voos, 0),
        1
    ) as taxa_realizacao_pct,

    -- Taxa de voos que saíram mas não chegaram ainda
    round(
        100.0 * voos_em_voo / nullif(total_voos, 0),
        1
    ) as taxa_em_voo_pct,

    -- Taxa de voos ainda programados
    round(
        100.0 * voos_programados / nullif(total_voos, 0),
        1
    ) as taxa_programado_pct

from agregado
