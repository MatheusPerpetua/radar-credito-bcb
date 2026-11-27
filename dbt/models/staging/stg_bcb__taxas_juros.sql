with fonte as (
    select * from {{ source('raw_bcb', 'taxas_juros') }}
)

select
    inicio_periodo,
    fim_periodo,
    case segmento
        when 'PESSOA FÍSICA' then 'PF'
        when 'PESSOA JURÍDICA' then 'PJ'
        else segmento
    end as segmento,
    modalidade,
    cnpj8,
    instituicao_financeira,
    posicao as posicao_ranking_bcb,
    cast(taxa_juros_ao_mes as numeric) as taxa_juros_am,
    cast(taxa_juros_ao_ano as numeric) as taxa_juros_aa,
    ingested_at
from fonte
