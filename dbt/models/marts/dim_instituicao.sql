-- Uma linha por instituição (raiz do CNPJ), com o nome mais recente publicado pelo BCB.
with ranqueado as (
    select
        cnpj8,
        instituicao_financeira,
        inicio_periodo,
        row_number() over (partition by cnpj8 order by inicio_periodo desc) as rn
    from {{ ref('stg_bcb__taxas_juros') }}
),

atividade as (
    select
        cnpj8,
        min(inicio_periodo) as primeira_publicacao,
        max(inicio_periodo) as ultima_publicacao,
        count(distinct modalidade) as qtd_modalidades
    from {{ ref('stg_bcb__taxas_juros') }}
    group by cnpj8
)

select
    r.cnpj8,
    r.instituicao_financeira as nome_instituicao,
    a.primeira_publicacao,
    a.ultima_publicacao,
    a.qtd_modalidades
from ranqueado as r
inner join atividade as a using (cnpj8)
where r.rn = 1
