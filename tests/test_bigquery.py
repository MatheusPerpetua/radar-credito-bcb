from datetime import date

import pandas as pd

from radar_bcb.load.bigquery import SGS_SERIES, TAXAS_JUROS, build_delete_sql


def test_delete_usa_intervalo_de_datas_parametrizado():
    df = pd.DataFrame({"inicio_periodo": [date(2026, 11, 3), date(2026, 11, 5)]})

    sql, params = build_delete_sql("proj.raw_bcb.taxas_juros", TAXAS_JUROS, df)

    assert sql == (
        "DELETE FROM `proj.raw_bcb.taxas_juros` "
        "WHERE inicio_periodo BETWEEN @data_min AND @data_max"
    )
    valores = {p.name: p.value for p in params}
    assert valores == {"data_min": date(2026, 11, 3), "data_max": date(2026, 11, 5)}


def test_delete_de_serie_sgs_restringe_ao_codigo_carregado():
    df = pd.DataFrame(
        {
            "codigo_serie": pd.array([433, 433], dtype="Int64"),
            "data": [date(2026, 9, 1), date(2026, 10, 1)],
        }
    )

    sql, params = build_delete_sql("proj.raw_bcb.sgs_series", SGS_SERIES, df)

    assert "codigo_serie IN UNNEST(@codigo_serie)" in sql
    codigos = next(p for p in params if p.name == "codigo_serie")
    assert codigos.values == [433]
