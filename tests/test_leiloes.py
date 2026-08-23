"""Testes do agregador. Rodar: PYTHONPATH=src python3 tests/test_leiloes.py"""

from __future__ import annotations

import gzip
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

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


def test_faixa_premium() -> None:
    assert suv_tier("I/LR Evoque Prestige 2.2 - 2015/2015") == "premium"
    assert suv_tier("FORD/ECOSPORT XLT1.6FLEX - 08/08") == "intermediario"
    assert suv_tier("Carro Chevrolet Celta 2P Life") is None


def test_teto_solar_so_quando_declarado() -> None:
    assert has_sunroof("Jeep Compass Limited com teto solar") is True
    assert has_sunroof("Jeep Compass Limited") is False


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
