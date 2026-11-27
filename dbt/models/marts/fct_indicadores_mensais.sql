-- Indicadores macro por mês: Selic média, IPCA do mês e acumulado em 12 meses,
-- juro real ex-post e a taxa mediana de mercado por segmento.
with selic_mensal as (
    select
        date_trunc(data, month) as mes,
        avg(valor) as selic_meta_media_aa
    from {{ ref('stg_bcb__sgs_series') }}
    where nome_serie = 'selic_meta'
      and data <= current_date()
    group by 1
),

ipca as (
    select
        date_trunc(data, month) as mes,
        valor as ipca_mes_pct
    from {{ ref('stg_bcb__sgs_series') }}
    where nome_serie = 'ipca_mensal'
),

ipca_12m as (
    select
        mes,
        ipca_mes_pct,
        case
            when count(*) over janela_12m = 12
                then (exp(sum(ln(1 + ipca_mes_pct / 100)) over janela_12m) - 1) * 100
        end as ipca_12m_pct
    from ipca
    window janela_12m as (order by mes rows between 11 preceding and current row)
),

mercado as (
    select
        date_trunc(inicio_periodo, month) as mes,
        approx_quantiles(if(segmento = 'PF', taxa_juros_aa, null), 2 ignore nulls)[offset(1)]
            as mediana_taxa_pf_aa,
        approx_quantiles(if(segmento = 'PJ', taxa_juros_aa, null), 2 ignore nulls)[offset(1)]
            as mediana_taxa_pj_aa
    from {{ ref('fct_taxas_juros') }}
    group by 1
)

select
    s.mes,
    s.selic_meta_media_aa,
    i.ipca_mes_pct,
    i.ipca_12m_pct,
    case
        when i.ipca_12m_pct is not null
            then ((1 + s.selic_meta_media_aa / 100) / (1 + i.ipca_12m_pct / 100) - 1) * 100
    end as juro_real_ex_post_aa,
    m.mediana_taxa_pf_aa,
    m.mediana_taxa_pj_aa
from selic_mensal as s
left join ipca_12m as i using (mes)
left join mercado as m using (mes)
