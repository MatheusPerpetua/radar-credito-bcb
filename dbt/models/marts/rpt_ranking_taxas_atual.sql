-- Ranking do período mais recente: quem cobra menos e quem cobra mais em cada modalidade.
-- Base do painel "quanto cada banco cobra hoje".
with ultimo_periodo as (
    select max(inicio_periodo) as inicio_periodo
    from {{ ref('fct_taxas_juros') }}
)

select
    f.inicio_periodo,
    f.fim_periodo,
    f.segmento,
    f.modalidade,
    f.cnpj8,
    i.nome_instituicao,
    f.taxa_juros_aa,
    f.taxa_juros_am,
    f.selic_meta_aa,
    f.spread_sobre_selic_pp,
    f.mediana_modalidade_aa,
    f.taxa_juros_aa - f.mediana_modalidade_aa as diferenca_mediana_pp,
    rank() over (
        partition by f.segmento, f.modalidade
        order by f.taxa_juros_aa
    ) as posicao_mais_barata,
    f.qtd_instituicoes_modalidade
from {{ ref('fct_taxas_juros') }} as f
inner join ultimo_periodo as u using (inicio_periodo)
left join {{ ref('dim_instituicao') }} as i using (cnpj8)
