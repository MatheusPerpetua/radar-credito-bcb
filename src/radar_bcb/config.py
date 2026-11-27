"""Configuração lida de variáveis de ambiente (ou de um arquivo .env local)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gcp_project: str
    bq_dataset_raw: str
    bq_location: str

    @classmethod
    def from_env(cls) -> Settings:
        project = os.getenv("GCP_PROJECT")
        if not project:
            raise RuntimeError("Defina GCP_PROJECT (veja .env.example).")
        return cls(
            gcp_project=project,
            bq_dataset_raw=os.getenv("BQ_DATASET_RAW", "raw_bcb"),
            bq_location=os.getenv("BQ_LOCATION", "southamerica-east1"),
        )
