"""Testes do agregador. Rodar: PYTHONPATH=src python3 tests/test_leiloes.py"""

from __future__ import annotations

import gzip
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from leiloes.anos import idade, parse_model_year  # noqa: E402
from leiloes.extract import is_sucata  # noqa: E402
from leiloes.catalog import classify_body, has_sunroof, suv_tier  # noqa: E402
from leiloes.finance import MIN_ENTRADA_PCT, RegraLegalError, simular  # noqa: E402
from leiloes.sources import leiloesjudiciais, megaleiloes  # noqa: E402
from leiloes.store import buscar, connect, upsert_many  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def ler_fixture(nome: str) -> str:
    """Amostras reais das paginas publicas, guardadas comprimidas."""
    return gzip.decompress((FIXTURES / f"{nome}.html.gz").read_bytes()).decode("utf-8")


def test_classificacao_de_carroceria() -> None:
    assert classify_body("I/BMW X5 M50D - 18/19 - Preta") == "suv"
    assert classify_body("Jeep/Compass Limited S - 20/21") == "suv"
    assert classify_body("Caminhão Volkswagen 8.150 E DELIVERYPLUS - 2010") == "nao_carro"
    assert classify_body("Direitos sobre Carro Toyota, Hilux - 2016/2017") == "picape"
    assert classify_body("Carro Chevrolet Celta 2P Life - 2006/2007") == "outro"


def test_nao_confunde_ano_cidade_e_versao_com_modelo() -> None:
    # "2008" aqui e ano, nao o Peugeot 2008.
    assert classify_body("I/PEUGEOT PART F 800K 16 - 2008/2009") == "outro"
    # "Santa Fe" aqui e cidade, nao o Hyundai Santa Fe.
    assert classify_body("VW SAVEIRO CL1.6 MI - 98/98 - Santa Fé do Sul/SP") == "picape"
    # "Edge" aqui e versao do Fiesta, nao o Ford Edge.
    assert classify_body("Ford Fiesta Edge - 03/03 - Osvaldo Cruz/SP") == "outro"
    # "GLS" aqui e acabamento, nao o Mercedes GLS.
    assert classify_body("Carro Chevrolet Vectra GLS - 1996/1997") == "outro"
    # Os modelos de verdade continuam passando.
    assert classify_body("Carro Peugeot 2008 Griffe 2019/2020") == "suv"
    assert classify_body("Carro Hyundai Santa Fe 3.5 V6 2013") == "suv"


def test_modelos_abreviados_e_familias() -> None:
    # Abreviacao de leiloeiro: "DEF130D" e o Land Rover Defender 130.
    assert classify_body("I/LR DEF130D X - 23/23 - São Paulo/SP") == "suv"
    # Pajero solto, Dakar e GLS sao SUV; nao so o Full e o Sport.
    for titulo in ("Carro Mitsubishi Pajero Dakar - 2010",
                   "I/Mitsubishi Pajero GLS - 01/01 - Rio de Janeiro/RJ",
                   "Mitsubishi/Pajero TR4. 2.0 - 09/10 - Taubaté/SP"):
        assert classify_body(titulo) == "suv", titulo
    # O TR4 e compacto: nao herda a faixa premium da familia Pajero.
    assert suv_tier("Mitsubishi/Pajero TR4. 2.0 - 09/10") == "intermediario"
    assert suv_tier("Carro Mitsubishi Pajero Sport HPE - 2006") == "premium"
    # Sedan, hatch e roadster de marca premium continuam fora.
    for titulo in ("I/VOLVO S60 2.0 T5 R-DES - 14/15",
                   "AUDI/A3 1.6 - 01/01 - Queiroz/SP",
                   "Carro BMW 550I NW51 SECURITY - 2008",
                   "Direitos sobre Carro Mercedes Benz A200 AMG LINE - 2023",
                   "Direitos sobre Carro Mercedes Benz SLK 200K - 2008"):
        assert classify_body(titulo) == "outro", titulo


def test_faixa_premium() -> None:
    assert suv_tier("I/LR Evoque Prestige 2.2 - 2015/2015") == "premium"
    assert suv_tier("FORD/ECOSPORT XLT1.6FLEX - 08/08") == "intermediario"
    assert suv_tier("Carro Chevrolet Celta 2P Life") is None


def test_teto_solar_so_quando_declarado() -> None:
    assert has_sunroof("Jeep Compass Limited com teto solar") is True
    assert has_sunroof("Jeep Compass Limited") is False


def test_ano_modelo_declarado() -> None:
    # Quatro digitos: vale o ano modelo, o segundo.
    assert parse_model_year("Carro Hyundai Creta Limited - 2023/2024") == 2024
    assert parse_model_year("Carro Mitsubishi, Pajero Sport HPE - 2019/2020") == 2020
    assert parse_model_year("Carro Chevrolet D20 Custom - 1985") == 1985
    # Dois digitos, como o leiloeiro costuma escrever.
    assert parse_model_year("I/LR DEF130D X - 23/23 - São Paulo/SP") == 2023
    assert parse_model_year("VW/T-Cross TSI MD - 19/20 - São José do Rio Preto/SP") == 2020
    assert parse_model_year("FORD/ECOSPORT XLT1.6FLEX – 08/09 – Itaquaquecetuba/SP") == 2009
    # Dois digitos antigos nao viram ano futuro.
    assert parse_model_year("Veículo Ford Jeep Universal 60/60 - Piquerobi/SP") == 1960
    # Rotulo na descricao do lote serve de reserva.
    assert parse_model_year("AUTOMÓVEL FORD/ECOSPORT, Ano/Modelo 2008/2009, Cor PRATA") == 2009
    # Anuncio sem ano nao vira palpite.
    assert parse_model_year("Ford/Ecosport XLS 1.6 Flex - Fortaleza/CE") is None
    assert idade(None) is None
    assert idade(2021, referencia=2026) == 5


def test_descricao_so_aceita_ano_rotulado() -> None:
    # Numero de processo tem ano dentro e ja foi lido como ano do carro.
    processo = ("AUTOMÓVEL FORD/ECOSPORT XLS 1.6 FLEX, placa HYN-6234. "
                "(Proc. 0001046-71.2023.5.07.0010) LOCALIZAÇÃO DO BEM: AV. CARAPINIMA")
    assert parse_model_year(processo, somente_rotulado=True) is None
    assert parse_model_year("no ano de 2023 o juízo determinou", somente_rotulado=True) is None
    # Rotulado, aceita.
    assert parse_model_year("Ano/Modelo 2008/2009, Cor PRATA", somente_rotulado=True) == 2009
    assert parse_model_year("ANO FAB/MOD: 2019/2020", somente_rotulado=True) == 2020


def test_sinistro_recuperado_conta_como_alerta() -> None:
    assert is_sucata("recuperado de um sinistro de média monta") is True
    assert is_sucata("veículo de grande monta") is True
    assert is_sucata("veículo em bom estado de conservação") is False


def test_filtro_de_idade_nao_inventa_ano(tmp_path: pathlib.Path | None = None) -> None:
    import tempfile

    from leiloes.models import Lote

    lotes = [
        Lote(source="t", source_id="novo", url="u1", title="Jeep Compass - 22/23", body="suv", price=90000.0, model_year=2023),
        Lote(source="t", source_id="velho", url="u2", title="Jeep Compass - 12/13", body="suv", price=40000.0, model_year=2013),
        Lote(source="t", source_id="semano", url="u3", title="Jeep Compass", body="suv", price=50000.0, model_year=None),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        conn = connect(str(pathlib.Path(tmp) / "t.db"))
        upsert_many(conn, lotes)
        recentes = {l["source_id"] for l in buscar(conn, body="suv", ano_min=2021)}
        assert recentes == {"novo"}, recentes
        # Sem ano declarado so entra quando pedido de forma explicita.
        com_desconhecidos = {l["source_id"] for l in buscar(conn, body="suv", ano_min=2021, incluir_sem_ano=True)}
        assert com_desconhecidos == {"novo", "semano"}, com_desconhecidos
        conn.close()


def test_regras_do_artigo_895() -> None:
    s = simular(60000)
    assert s.entrada == 15000.0
    assert s.parcela == 1500.0
    assert s.comissao_leiloeiro == 3000.0
    assert s.desembolso_inicial == 18000.0
    for proibido in ({"entrada_pct": 0.0}, {"entrada_pct": 0.1}, {"parcelas": 48}):
        try:
            simular(60000, **proibido)
        except RegraLegalError:
            continue
        raise AssertionError(f"deveria recusar {proibido}")
    assert MIN_ENTRADA_PCT == 0.25


def test_parser_megaleiloes() -> None:
    lotes = megaleiloes.parse_listing(ler_fixture("megaleiloes_carros"))
    assert len(lotes) >= 40
    por_id = {l.source_id: l for l in lotes}
    evoque = por_id["J125859"]
    assert evoque.title.startswith("Carro Land Rover Evoque")
    assert evoque.price == 1.0          # o site publica o lance corrente
    assert evoque.discount_pct == 50
    assert evoque.city == "São Paulo" and evoque.uf == "SP"
    assert evoque.modality == "Judicial"
    assert evoque.body == "suv" and evoque.tier == "premium"
    assert evoque.url.startswith("https://www.megaleiloes.com.br/")


def test_parser_leiloesjudiciais() -> None:
    lotes = leiloesjudiciais.parse_listing(ler_fixture("leiloesjudiciais_veiculos"))
    assert len(lotes) >= 40
    primeiro = lotes[0]
    assert primeiro.url.startswith("https://www.leiloesjudiciais.com.br/lote/")
    assert primeiro.appraisal and primeiro.appraisal > 0
    assert primeiro.uf and len(primeiro.uf) == 2


def test_store_filtra_apenas_suv(tmp_path: pathlib.Path | None = None) -> None:
    import tempfile

    lotes = megaleiloes.parse_listing(ler_fixture("megaleiloes_carros"))
    with tempfile.TemporaryDirectory() as tmp:
        conn = connect(str(pathlib.Path(tmp) / "t.db"))
        upsert_many(conn, lotes)
        suvs = buscar(conn, body="suv")
        assert suvs, "esperava ao menos um SUV na amostra"
        assert all(l["body"] == "suv" for l in suvs)
        assert all(l["url"] for l in suvs), "todo lote precisa carregar a origem"
        premium = buscar(conn, body="suv", tier="premium")
        assert all(l["tier"] == "premium" for l in premium)
        conn.close()


def main() -> int:
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for teste in testes:
        try:
            teste()
        except AssertionError as erro:
            falhas += 1
            print(f"FALHOU {teste.__name__}: {erro}")
        else:
            print(f"ok     {teste.__name__}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
