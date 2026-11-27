"""Flows Prefect do Radar de Crédito.

Uso:
    python -m flows.pipeline                 # roda o pipeline uma vez (ex.: Cloud Run Job)
    python -m flows.pipeline --serve         # agenda localmente (cron diário) e fica ouvindo
    python -m flows.pipeline --dias 90       # reprocessa uma janela maior
    python -m flows.pipeline --sem-dbt       # só extração e carga
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import date, timedelta
from pathlib import Path

from prefect import flow, get_run_logger, task

from radar_bcb.config import Settings
from radar_bcb.extract import olinda, sgs
from radar_bcb.load.bigquery import SGS_SERIES, TAXAS_JUROS, BigQueryLoader

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"
RETRY_DELAYS = [30, 120, 600]


@task(retries=3, retry_delay_seconds=RETRY_DELAYS, log_prints=True)
def extrair_taxas_juros(inicio: date):
    df = olinda.fetch_taxas_juros(inicio)
    print(f"Taxas de juros: {len(df)} linhas desde {inicio}")
    return df


@task(retries=3, retry_delay_seconds=RETRY_DELAYS, log_prints=True)
def extrair_serie_sgs(codigo: int, inicio: date, fim: date):
    df = sgs.fetch_serie(codigo, inicio, fim)
    print(f"SGS {codigo} ({sgs.SERIES.get(codigo)}): {len(df)} linhas")
    return df


@task(retries=2, retry_delay_seconds=[60, 300])
def carregar(tabela, df) -> int:
    loader = BigQueryLoader(Settings.from_env())
    return loader.replace_range(tabela, df)


@task(log_prints=True)
def rodar_dbt(comando: str = "build") -> None:
    resultado = subprocess.run(
        ["dbt", comando, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    print(resultado.stdout)
    if resultado.returncode != 0:
        raise RuntimeError(f"dbt {comando} falhou:\n{resultado.stderr or resultado.stdout}")


@flow(name="ingestao-taxas-juros")
def ingestao_taxas_juros(dias: int = 21) -> int:
    inicio = date.today() - timedelta(days=dias)
    df = extrair_taxas_juros(inicio)
    return carregar(TAXAS_JUROS, df)


@flow(name="ingestao-sgs")
def ingestao_sgs(dias: int = 400) -> int:
    fim = date.today() + timedelta(days=60)  # a meta Selic já vem publicada para datas futuras
    inicio = date.today() - timedelta(days=dias)
    total = 0
    for codigo in sgs.SERIES:
        df = extrair_serie_sgs(codigo, inicio, fim)
        total += carregar(SGS_SERIES, df)
    return total


@flow(name="radar-credito-bcb")
def pipeline(dias_taxas: int = 21, dias_sgs: int = 400, com_dbt: bool = True) -> None:
    logger = get_run_logger()
    linhas_taxas = ingestao_taxas_juros(dias_taxas)
    linhas_sgs = ingestao_sgs(dias_sgs)
    logger.info("Carga concluída: %s linhas de taxas, %s de séries SGS", linhas_taxas, linhas_sgs)
    if com_dbt:
        rodar_dbt("deps")
        rodar_dbt("build")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--serve", action="store_true", help="agenda o flow (cron diário)")
    parser.add_argument("--dias", type=int, default=21, help="janela de taxas de juros")
    parser.add_argument("--sem-dbt", action="store_true", help="não roda o dbt ao final")
    args = parser.parse_args()

    if args.serve:
        pipeline.serve(
            name="radar-credito-diario",
            cron="0 10 * * *",  # 10h UTC = 7h em Brasília
            parameters={"dias_taxas": args.dias, "com_dbt": not args.sem_dbt},
        )
    else:
        pipeline(dias_taxas=args.dias, com_dbt=not args.sem_dbt)


if __name__ == "__main__":
    main()
