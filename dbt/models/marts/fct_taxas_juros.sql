-- Taxa de cada instituição por modalidade e período, comparada com a meta Selic
-- vigente no início do período e com a mediana do mercado na mesma modalidade.
with taxas as (
    select * from {{ ref('stg_bcb__taxas_juros') }}
),

selic as (
    select
        data as vigente_desde,
        lead(data) over (order by data) as vigente_ate,
        cast(valor as numeric) as selic_meta_aa
    from {{ ref('stg_bcb__sgs_series') }}
    where nome_serie = 'selic_meta'
),

com_selic as (
    select
        t.*,
        s.selic_meta_aa
    from taxas as t
    left join selic as s
        on t.inicio_periodo >= s.vigente_desde
        and (s.vigente_ate is null or t.inicio_periodo < s.vigente_ate)
)

select
    {{ dbt_utils.generate_surrogate_key(['inicio_periodo', 'segmento', 'modalidade', 'cnpj8']) }}
        as id_taxa,
    inicio_periodo,
    fim_periodo,
    segmento,
    modalidade,
    cnpj8,
    posicao_ranking_bcb,
    taxa_juros_am,
    taxa_juros_aa,
    selic_meta_aa,
    taxa_juros_aa - selic_meta_aa as spread_sobre_selic_pp,
    percentile_cont(taxa_juros_aa, 0.5) over (
        partition by inicio_periodo, segmento, modalidade
    ) as mediana_modalidade_aa,
    count(*) over (partition by inicio_periodo, segmento, modalidade) as qtd_instituicoes_modalidade
from com_selic
