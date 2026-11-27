"""Carga idempotente no BigQuery.

Estratégia: as tabelas raw são particionadas por data. A cada execução, apagamos o
intervalo de datas que está sendo recarregado e inserimos os dados novos. Assim, rodar
o mesmo período duas vezes não duplica linhas, e reprocessar um período é seguro.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from google.cloud import bigquery

from radar_bcb.config import Settings

F = bigquery.SchemaField


@dataclass(frozen=True)
class RawTable:
    name: str
    partition_field: str
    cluster_fields: tuple[str, ...]
    schema: tuple[bigquery.SchemaField, ...]
    # Colunas que, junto com a data, identificam o subconjunto recarregado.
    scope_fields: tuple[str, ...] = ()


TAXAS_JUROS = RawTable(
    name="taxas_juros",
    partition_field="inicio_periodo",
    cluster_fields=("segmento", "modalidade"),
    schema=(
        F("inicio_periodo", "DATE", mode="REQUIRED"),
        F("fim_periodo", "DATE"),
        F("segmento", "STRING"),
        F("modalidade", "STRING"),
        F("posicao", "INT64"),
        F("instituicao_financeira", "STRING"),
        F("cnpj8", "STRING"),
        F("taxa_juros_ao_mes", "FLOAT64"),
        F("taxa_juros_ao_ano", "FLOAT64"),
        F("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ),
)

SGS_SERIES = RawTable(
    name="sgs_series",
    partition_field="data",
    cluster_fields=("codigo_serie",),
    schema=(
        F("codigo_serie", "INT64", mode="REQUIRED"),
        F("nome_serie", "STRING"),
        F("data", "DATE", mode="REQUIRED"),
        F("valor", "FLOAT64"),
        F("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    scope_fields=("codigo_serie",),
)


def build_delete_sql(table_id: str, table: RawTable, df: pd.DataFrame) -> tuple[str, list]:
    """Monta o DELETE do intervalo que será recarregado (com parâmetros, sem concatenar valores)."""
    col = table.partition_field
    where = [f"{col} BETWEEN @data_min AND @data_max"]
    params: list = [
        bigquery.ScalarQueryParameter("data_min", "DATE", df[col].min()),
        bigquery.ScalarQueryParameter("data_max", "DATE", df[col].max()),
    ]
    for field in table.scope_fields:
        valores = [int(v) for v in df[field].dropna().unique()]
        where.append(f"{field} IN UNNEST(@{field})")
        params.append(bigquery.ArrayQueryParameter(field, "INT64", valores))
    return f"DELETE FROM `{table_id}` WHERE " + " AND ".join(where), params


class BigQueryLoader:
    def __init__(self, settings: Settings, client: bigquery.Client | None = None):
        self.settings = settings
        self.client = client or bigquery.Client(
            project=settings.gcp_project, location=settings.bq_location
        )

    def _table_id(self, table: RawTable) -> str:
        return f"{self.settings.gcp_project}.{self.settings.bq_dataset_raw}.{table.name}"

    def ensure_table(self, table: RawTable) -> None:
        dataset = bigquery.Dataset(f"{self.settings.gcp_project}.{self.settings.bq_dataset_raw}")
        dataset.location = self.settings.bq_location
        self.client.create_dataset(dataset, exists_ok=True)

        bq_table = bigquery.Table(self._table_id(table), schema=list(table.schema))
        bq_table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.MONTH, field=table.partition_field
        )
        bq_table.clustering_fields = list(table.cluster_fields)
        self.client.create_table(bq_table, exists_ok=True)

    def replace_range(self, table: RawTable, df: pd.DataFrame) -> int:
        """Apaga o intervalo de datas de ``df``, insere ``df`` e retorna as linhas gravadas."""
        if df.empty:
            return 0
        self.ensure_table(table)
        table_id = self._table_id(table)

        df = df.copy()
        df["ingested_at"] = datetime.now(UTC)

        sql, params = build_delete_sql(table_id, table, df)
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        self.client.query(sql, job_config=job_config).result()

        load_config = bigquery.LoadJobConfig(
            schema=list(table.schema),
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        self.client.load_table_from_dataframe(df, table_id, job_config=load_config).result()
        return len(df)
