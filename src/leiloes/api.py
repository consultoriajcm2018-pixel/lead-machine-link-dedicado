"""API HTTP e interface web do agregador."""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

import datetime as dt

from . import store
from .anos import idade
from .finance import MAX_PARCELAS, MIN_ENTRADA_PCT, RegraLegalError, simular
from .sync import sincronizar

WEB_DIR = pathlib.Path(__file__).parent / "web"

app = FastAPI(
    title="Radar de SUVs em leilao judicial",
    description=(
        "Agrega lotes publicados por leiloeiros oficiais. Cada item traz o link "
        "da origem. Nenhum dado e estimado."
    ),
    version="0.1.0",
)


def _preco_confiavel(valor: float | None) -> bool:
    """Valores simbolicos (R$ 1,00) na listagem indicam lance corrente, nao preco."""
    return bool(valor and valor >= 1000)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/lotes")
def listar_lotes(
    body: str = Query("suv", description="carrocerias separadas por virgula: suv, crossover, picape"),
    tier: str | None = None,
    uf: str | None = None,
    incluir_sem_uf: bool = False,
    entrada_max: float | None = Query(None, description="teto para a entrada de 25%; corta pelo valor do lote"),
    preco_min: float | None = None,
    preco_max: float | None = None,
    desconto_min: int | None = None,
    teto_solar: bool = False,
    idade_max: int | None = Query(5, ge=0, le=60, description="anos de uso maximos; o padrao e 5"),
    incluir_sem_ano: bool = False,
    excluir_sucata: bool = True,
    excluir_direitos: bool = False,
    so_parcelavel: bool = False,
    termo: str | None = None,
    ordem: str = "parcela",
    limite: int = Query(200, le=500),
    entrada_pct: float = MIN_ENTRADA_PCT,
    parcelas: int = MAX_PARCELAS,
) -> JSONResponse:
    ano_min = dt.date.today().year - idade_max if idade_max is not None else None

    # Entrada e percentual do lance, entao um teto de entrada vira teto de valor.
    if entrada_max is not None and entrada_pct > 0:
        limite = entrada_max / entrada_pct
        preco_max = min(preco_max, limite) if preco_max is not None else limite

    conn = store.connect()
    try:
        linhas = store.buscar(
            conn,
            body=[b.strip() for b in body.split(",") if b.strip()] or None,
            tier=tier,
            uf=uf,
            incluir_sem_uf=incluir_sem_uf,
            preco_min=preco_min,
            preco_max=preco_max,
            desconto_min=desconto_min,
            teto_solar=teto_solar,
            ano_min=ano_min,
            incluir_sem_ano=incluir_sem_ano,
            excluir_sucata=excluir_sucata,
            excluir_direitos=excluir_direitos,
            so_parcelavel=so_parcelavel,
            termo=termo,
            ordem=ordem,
            limite=limite,
        )
        atualizado = store.get_meta(conn, "ultima_sincronizacao")
    finally:
        conn.close()

    for linha in linhas:
        linha["preco_confiavel"] = _preco_confiavel(linha.get("price"))
        linha["teto_solar"] = "sim" if linha.get("sunroof") else "nao informado"
        linha["parcelamento"] = linha.get("payment_terms") or "nao declarado no anuncio"
        linha["sucata"] = bool(linha.get("scrap"))
        anos = idade(linha.get("model_year"))
        linha["idade"] = anos
        linha["ano_modelo"] = linha.get("model_year") or "nao declarado"
        linha["so_direitos"] = bool(linha.get("rights_only"))
        linha.pop("description", None)
        if linha["preco_confiavel"]:
            s = simular(linha["price"], entrada_pct=entrada_pct, parcelas=parcelas)
            linha["entrada"] = s.entrada
            linha["parcela"] = s.parcela
            linha["desembolso_inicial"] = s.desembolso_inicial
        else:
            linha["entrada"] = linha["parcela"] = linha["desembolso_inicial"] = None

    if ordem == "parcela":
        linhas.sort(key=lambda l: (l["parcela"] is None, l["parcela"] or 0))

    return JSONResponse(
        {
            "atualizado_em": atualizado,
            "total": len(linhas),
            "regra_de_entrada": {
                "entrada_max": entrada_max,
                "valor_de_lote_maximo": preco_max,
            },
            "regra_de_idade": {
                "idade_maxima": idade_max,
                "ano_modelo_minimo": ano_min,
                "sem_ano_declarado_incluidos": incluir_sem_ano,
            },
            "regra_de_parcelamento": {
                "base_legal": "CPC (Lei 13.105/2015), art. 895",
                "entrada_minima": MIN_ENTRADA_PCT,
                "parcelas_maximas": MAX_PARCELAS,
                "entrada_zero_permitida": False,
            },
            "lotes": linhas,
        }
    )


@app.get("/api/simulacao")
def simulacao(
    valor: float,
    entrada_pct: float = MIN_ENTRADA_PCT,
    parcelas: int = MAX_PARCELAS,
) -> JSONResponse:
    try:
        resultado = simular(valor, entrada_pct=entrada_pct, parcelas=parcelas)
    except RegraLegalError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return JSONResponse(resultado.__dict__ if not hasattr(resultado, "__dataclass_fields__") else {
        campo: getattr(resultado, campo) for campo in resultado.__dataclass_fields__
    })


@app.post("/api/sync")
def sync(paginas: int = 6, detalhes: int = 60) -> JSONResponse:
    return JSONResponse(sincronizar(max_pages=paginas, detalhes=detalhes))
