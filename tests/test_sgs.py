from datetime import date

from radar_bcb.extract import sgs


def test_janelas_cobrem_o_intervalo_sem_sobreposicao():
    inicio, fim = date(2010, 1, 1), date(2026, 11, 27)
    janelas = sgs._janelas(inicio, fim)

    assert janelas[0][0] == inicio
    assert janelas[-1][1] == fim
    for (_, fim_a), (ini_b, _) in zip(janelas, janelas[1:], strict=False):
        assert (ini_b - fim_a).days == 1
    assert all((fi - ini) <= sgs.JANELA_MAX for ini, fi in janelas)


def test_normaliza_datas_brasileiras_e_remove_duplicadas():
    registros = [
        {"data": "01/10/2026", "valor": "0.14"},
        {"data": "01/09/2026", "valor": "0.82"},
        {"data": "01/10/2026", "valor": "0.15"},
    ]
    df = sgs.normalize(433, registros)

    assert len(df) == 2
    assert set(df["nome_serie"]) == {"ipca_mensal"}
    outubro = df[df["data"] == date(2026, 10, 1)].iloc[0]
    assert outubro["valor"] == 0.15


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("não deveria chamar raise_for_status com erro aqui")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, respostas):
        self.respostas = list(respostas)

    def get(self, url, params=None, timeout=None):
        return self.respostas.pop(0)


def test_janela_sem_dados_404_e_ignorada(monkeypatch):
    monkeypatch.setattr(sgs, "_janelas", lambda i, f: [(i, i), (f, f)])
    session = FakeSession(
        [
            FakeResponse(404),
            FakeResponse(200, [{"data": "27/11/2026", "valor": "15.00"}]),
        ]
    )

    df = sgs.fetch_serie(432, date(2026, 1, 1), date(2026, 11, 27), session=session)

    assert len(df) == 1
    assert df.iloc[0]["nome_serie"] == "selic_meta"
