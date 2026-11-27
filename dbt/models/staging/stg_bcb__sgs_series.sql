select
    codigo_serie,
    nome_serie,
    data,
    valor
from {{ source('raw_bcb', 'sgs_series') }}
where valor is not null
