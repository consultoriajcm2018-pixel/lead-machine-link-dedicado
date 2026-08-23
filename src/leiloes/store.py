"""Persistencia em SQLite. Um registro por lote, chaveado por origem+id."""

from __future__ import annotations

import dataclasses
import datetime as dt
import os
import sqlite3
from typing import Any, Iterable

from .models import Lote

DB_PATH = os.environ.get("LEILOES_DB", "leiloes.db")

FIELDS = [f.name for f in dataclasses.fields(Lote)]
NUMERICOS = ("price", "appraisal", "discount_pct", "sunroof", "scrap", "rights_only")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS lotes (
    key TEXT PRIMARY KEY,
    {", ".join(f"{name} TEXT" for name in FIELDS if name not in NUMERICOS)},
    price REAL,
    appraisal REAL,
    discount_pct INTEGER,
    sunroof INTEGER,
    scrap INTEGER,
    rights_only INTEGER
);
CREATE INDEX IF NOT EXISTS idx_lotes_body ON lotes(body);
CREATE INDEX IF NOT EXISTS idx_lotes_price ON lotes(price);
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_many(conn: sqlite3.Connection, lotes: Iterable[Lote]) -> int:
    columns = ["key"] + FIELDS
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c}=excluded.{c}" for c in FIELDS)
    sql = (
        f"INSERT INTO lotes ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT(key) DO UPDATE SET {updates}"
    )
    rows = []
    for lote in lotes:
        data = lote.to_dict()
        rows.append([lote.key()] + [data[name] for name in FIELDS])
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def set_meta(conn: sqlite3.Connection, chave: str, valor: str) -> None:
    conn.execute(
        "INSERT INTO meta (chave, valor) VALUES (?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
        (chave, valor),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, chave: str) -> str | None:
    row = conn.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    return row["valor"] if row else None


def stamp_sync(conn: sqlite3.Connection) -> str:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    set_meta(conn, "ultima_sincronizacao", now)
    return now


def buscar(
    conn: sqlite3.Connection,
    body: str | None = "suv",
    tier: str | None = None,
    uf: str | None = None,
    preco_max: float | None = None,
    preco_min: float | None = None,
    desconto_min: int | None = None,
    teto_solar: bool = False,
    excluir_sucata: bool = True,
    excluir_direitos: bool = False,
    so_parcelavel: bool = False,
    termo: str | None = None,
    ordem: str = "parcela",
    limite: int = 200,
) -> list[dict[str, Any]]:
    where = ["price IS NOT NULL"]
    params: list[Any] = []
    if body:
        where.append("body = ?")
        params.append(body)
    if tier:
        where.append("tier = ?")
        params.append(tier)
    if uf:
        where.append("UPPER(uf) = ?")
        params.append(uf.upper())
    if preco_max is not None:
        where.append("price <= ?")
        params.append(preco_max)
    if preco_min is not None:
        where.append("price >= ?")
        params.append(preco_min)
    if desconto_min is not None:
        where.append("discount_pct >= ?")
        params.append(desconto_min)
    if teto_solar:
        where.append("sunroof = 1")
    if excluir_sucata:
        where.append("COALESCE(scrap, 0) = 0")
    if excluir_direitos:
        where.append("COALESCE(rights_only, 0) = 0")
    if so_parcelavel:
        where.append("payment_terms <> 'somente a vista'")
    if termo:
        where.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
        like = f"%{termo.lower()}%"
        params += [like, like]

    order_sql = {
        "parcela": "price ASC",
        "preco": "price ASC",
        "preco_desc": "price DESC",
        "desconto": "discount_pct DESC, price ASC",
    }.get(ordem, "price ASC")

    sql = f"SELECT * FROM lotes WHERE {' AND '.join(where)} ORDER BY {order_sql} LIMIT ?"
    params.append(limite)
    return [dict(row) for row in conn.execute(sql, params).fetchall()]
