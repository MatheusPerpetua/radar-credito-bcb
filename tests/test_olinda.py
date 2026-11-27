from datetime import date

from radar_bcb.extract import olinda


def _linha(i: int) -> dict:
    return {
        "InicioPeriodo": "2026-11-05",
        "FimPeriodo": "2026-11-11",
        "Segmento": " PESSOA FÍSICA ",
        "Modalidade": "Crédito pessoal não consignado",
        "Posicao": i,
        "InstituicaoFinanceira": f"BANCO {i}",
        "cnpj8": f"{i:08d}",
        "TaxaJurosAoMes": 5.1,
        "TaxaJurosAoAno": 81.6,
    }


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, paginas):
        self.paginas = list(paginas)
        self.urls: list[str] = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        return FakeResponse({"value": self.paginas.pop(0)})


def test_pagina_ate_receber_pagina_incompleta(monkeypatch):
    monkeypatch.setattr(olinda, "PAGE_SIZE", 2)
    session = FakeSession([[_linha(1), _linha(2)], [_linha(3)]])

    df = olinda.fetch_taxas_juros(date(2026, 11, 1), session=session)

    assert len(df) == 3
    assert len(session.urls) == 2
    assert "$skip=2" in session.urls[1]


def test_espacos_do_filtro_sao_codificados_como_percent20():
    session = FakeSession([[]])
    olinda.fetch_taxas_juros(date(2026, 11, 1), date(2026, 11, 30), session=session)

    url = session.urls[0]
    assert "+" not in url
    assert "InicioPeriodo%20ge%20'2026-11-01'%20and%20InicioPeriodo%20le%20'2026-11-30'" in url


def test_normaliza_tipos_e_nomes():
    df = olinda.normalize([_linha(7)])

    assert list(df.columns) == list(olinda.COLUMNS.values())
    linha = df.iloc[0]
    assert linha["inicio_periodo"] == date(2026, 11, 5)
    assert linha["segmento"] == "PESSOA FÍSICA"
    assert linha["cnpj8"] == "00000007"
    assert linha["taxa_juros_ao_ano"] == 81.6


def test_normaliza_lista_vazia():
    df = olinda.normalize([])
    assert df.empty
    assert "taxa_juros_ao_ano" in df.columns
