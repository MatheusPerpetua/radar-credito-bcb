"""Taxas de juros por instituição e modalidade — API Olinda do Banco Central.

Fonte: https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito
Cada linha é a taxa média praticada por uma instituição, numa modalidade, num período
de 5 dias úteis (``InicioPeriodo`` → ``FimPeriodo``). Os períodos são janelas móveis:
um novo começa a cada dia útil. Grão: inicio_periodo + segmento + modalidade + cnpj8.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import quote, urlencode

import pandas as pd
import requests

from radar_bcb.http import TIMEOUT, build_session

BASE_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/"
    "TaxasJurosDiariaPorInicioPeriodo"
)
PAGE_SIZE = 10_000

COLUMNS = {
    "InicioPeriodo": "inicio_periodo",
    "FimPeriodo": "fim_periodo",
    "Segmento": "segmento",
    "Modalidade": "modalidade",
    "Posicao": "posicao",
    "InstituicaoFinanceira": "instituicao_financeira",
    "cnpj8": "cnpj8",
    "TaxaJurosAoMes": "taxa_juros_ao_mes",
    "TaxaJurosAoAno": "taxa_juros_ao_ano",
}


def fetch_taxas_juros(
    inicio: date,
    fim: date | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Baixa todas as linhas com ``InicioPeriodo`` entre ``inicio`` e ``fim`` (inclusive)."""
    session = session or build_session()
    filtro = f"InicioPeriodo ge '{inicio.isoformat()}'"
    if fim:
        filtro += f" and InicioPeriodo le '{fim.isoformat()}'"

    registros: list[dict] = []
    skip = 0
    while True:
        params = {
            "$format": "json",
            "$filter": filtro,
            "$select": ",".join(COLUMNS),
            "$orderby": "InicioPeriodo,Segmento,Modalidade,Posicao",
            "$top": PAGE_SIZE,
            "$skip": skip,
        }
        # O Olinda rejeita espaços codificados como "+": é preciso usar "%20".
        query = urlencode(params, quote_via=quote, safe="$,'")
        resp = session.get(f"{BASE_URL}?{query}", timeout=TIMEOUT)
        resp.raise_for_status()
        pagina = resp.json().get("value", [])
        registros.extend(pagina)
        if len(pagina) < PAGE_SIZE:
            break
        skip += PAGE_SIZE

    return normalize(registros)


def normalize(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros, columns=list(COLUMNS)).rename(columns=COLUMNS)
    df["inicio_periodo"] = pd.to_datetime(df["inicio_periodo"]).dt.date
    df["fim_periodo"] = pd.to_datetime(df["fim_periodo"]).dt.date
    for col in ("segmento", "modalidade", "instituicao_financeira", "cnpj8"):
        df[col] = df[col].astype("string").str.strip()
    df["posicao"] = df["posicao"].astype("Int64")
    for col in ("taxa_juros_ao_mes", "taxa_juros_ao_ano"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
