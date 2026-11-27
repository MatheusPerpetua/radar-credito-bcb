"""Séries temporais do SGS (Sistema Gerenciador de Séries) do Banco Central.

Fonte: https://dadosabertos.bcb.gov.br/dataset/sgs
A API limita consultas de séries diárias a janelas de 10 anos, então a extração
é feita em blocos.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import requests

from radar_bcb.http import TIMEOUT, build_session

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
JANELA_MAX = timedelta(days=365 * 5)

# Séries usadas no projeto. Para adicionar uma, inclua o código SGS aqui.
SERIES: dict[int, str] = {
    432: "selic_meta",  # Meta Selic definida pelo Copom (% a.a.), diária
    433: "ipca_mensal",  # IPCA, variação mensal (%)
}


def _janelas(inicio: date, fim: date) -> list[tuple[date, date]]:
    janelas = []
    atual = inicio
    while atual <= fim:
        fim_janela = min(atual + JANELA_MAX, fim)
        janelas.append((atual, fim_janela))
        atual = fim_janela + timedelta(days=1)
    return janelas


def fetch_serie(
    codigo: int,
    inicio: date,
    fim: date,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Baixa uma série do SGS entre ``inicio`` e ``fim`` (inclusive)."""
    session = session or build_session()
    registros: list[dict] = []
    for ini, fi in _janelas(inicio, fim):
        params = {
            "formato": "json",
            "dataInicial": ini.strftime("%d/%m/%Y"),
            "dataFinal": fi.strftime("%d/%m/%Y"),
        }
        resp = session.get(BASE_URL.format(codigo=codigo), params=params, timeout=TIMEOUT)
        # O SGS responde 404 quando não há dados na janela pedida.
        if resp.status_code == 404:
            continue
        resp.raise_for_status()
        registros.extend(resp.json())
    return normalize(codigo, registros)


def normalize(codigo: int, registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros, columns=["data", "valor"])
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.date
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df.insert(0, "codigo_serie", codigo)
    df.insert(1, "nome_serie", SERIES.get(codigo, str(codigo)))
    df["codigo_serie"] = df["codigo_serie"].astype("Int64")
    return df.drop_duplicates(subset=["codigo_serie", "data"], keep="last")
