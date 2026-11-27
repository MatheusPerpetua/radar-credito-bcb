"""Sessão HTTP compartilhada, com retry para as instabilidades das APIs do BCB."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = (10, 120)  # (conexão, leitura) em segundos — a API Olinda pode ser lenta


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "radar-credito-bcb"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session
