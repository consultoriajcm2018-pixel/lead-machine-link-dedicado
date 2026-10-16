"""Coleta os lotes publicados nas origens e grava no banco local."""

from __future__ import annotations

import sqlite3

from . import store
from .http import build_client
from .models import Lote
from .sources import REGISTRY


def coletar(max_pages: int = 6) -> list[Lote]:
    lotes: list[Lote] = []
    with build_client() as client:
        for module in REGISTRY.values():
            lotes.extend(module.collect(client, max_pages=max_pages))
    return lotes


def detalhar(lotes: list[Lote], limite: int = 60) -> list[Lote]:
    """Abre a pagina de cada SUV para ler descricao, avaliacao e teto solar."""
    alvos = [l for l in lotes if l.body in ("suv", "crossover")][:limite]
    if not alvos:
        return lotes
    with build_client() as client:
        for lote in alvos:
            REGISTRY[lote.source].enrich(client, lote)
    return lotes


def sincronizar(
    db_path: str | None = None,
    max_pages: int = 6,
    detalhes: int = 60,
) -> dict[str, object]:
    lotes = coletar(max_pages=max_pages)
    detalhar(lotes, limite=detalhes)
    conn: sqlite3.Connection = store.connect(db_path)
    try:
        gravados = store.upsert_many(conn, lotes)
        quando = store.stamp_sync(conn)
    finally:
        conn.close()
    suvs = [l for l in lotes if l.body == "suv"]
    crossovers = [l for l in lotes if l.body == "crossover"]
    return {
        "lotes_coletados": gravados,
        "suvs": len(suvs),
        "crossovers": len(crossovers),
        "suvs_premium": sum(1 for l in suvs if l.tier == "premium"),
        "com_teto_solar_declarado": sum(1 for l in suvs if l.sunroof),
        "sincronizado_em": quando,
        "origens": sorted(REGISTRY),
    }
