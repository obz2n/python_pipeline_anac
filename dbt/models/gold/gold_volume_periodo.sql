-- gold_volume_periodo (PostgreSQL-compatible)
-- Volume de voos por período (mês e trimestre), com variação percentual
-- mês a mês — útil para identificar sazonalidade e tendências.

with silver as (

    select * from {{ ref('silver_voos') }}
    where ano is not null and mes is not null

),

agregado_mensal as (

    select
        ano,
        mes,
        nome_mes,
        trimestre,
        nm_regiao_origem,

        count(*) as total_voos,
        SUM(CASE WHEN flag_situacao = 'realizado' THEN 1 ELSE 0 END) as voos_realizados,
        SUM(CASE WHEN flag_situacao = 'em_voo' THEN 1 ELSE 0 END) as voos_em_voo,
        SUM(CASE WHEN flag_situacao = 'programado' THEN 1 ELSE 0 END) as voos_programados,
        count(distinct sg_empresa_icao) as qtd_empresas_ativas,
        count(distinct rota) as qtd_rotas_ativas

    from silver
    group by ano, mes, nome_mes, trimestre, nm_regiao_origem

),

com_variacao as (

    select
        *,

        -- Volume do mesmo período no mês anterior (mesma região), para cálculo de variação
        lag(total_voos) over (
            partition by nm_regiao_origem
            order by ano, mes
        ) as total_voos_mes_anterior

    from agregado_mensal

)

select
    *,

    round(
        100.0 * (total_voos - total_voos_mes_anterior) / nullif(total_voos_mes_anterior, 0),
        1
    ) as variacao_pct_mes_anterior

from com_variacao
