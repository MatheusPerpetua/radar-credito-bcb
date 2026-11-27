# Imagem para rodar o pipeline como Cloud Run Job (uma execução por disparo do Cloud Scheduler).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[dbt]"

COPY flows ./flows
COPY dbt ./dbt
RUN cd dbt && dbt deps --profiles-dir .

ENV DBT_TARGET=prod
CMD ["python", "-m", "flows.pipeline"]
