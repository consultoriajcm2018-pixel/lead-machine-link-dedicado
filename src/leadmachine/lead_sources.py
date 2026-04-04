from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from .db import session_scope
from .models import Lead


@dataclass
class LeadInput:
    nome_empresa: str
    telefone: str
    email: str
    segmento: str
    cidade: str


REQUIRED_COLUMNS = ['nome_empresa', 'telefone', 'email', 'segmento', 'cidade']


def import_from_csv(path: str) -> int:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f'CSV sem colunas obrigatórias: {missing}')

    imported = 0
    with session_scope() as session:
        for _, row in df.iterrows():
            if session.query(Lead).filter_by(telefone=str(row['telefone'])).first():
                continue
            lead = Lead(
                nome_empresa=str(row['nome_empresa']).strip(),
                telefone=str(row['telefone']).strip(),
                email=str(row['email']).strip(),
                segmento=str(row['segmento']).strip(),
                cidade=str(row['cidade']).strip(),
            )
            session.add(lead)
            imported += 1
    return imported


def import_from_database(query: str, db_url: str) -> int:
    from sqlalchemy import create_engine

    ext_engine = create_engine(db_url)
    imported = 0
    with ext_engine.connect() as conn:
        rows = conn.execute(text(query)).mappings().all()

    with session_scope() as session:
        for row in rows:
            if session.query(Lead).filter_by(telefone=str(row['telefone'])).first():
                continue
            lead = Lead(
                nome_empresa=str(row['nome_empresa']).strip(),
                telefone=str(row['telefone']).strip(),
                email=str(row['email']).strip(),
                segmento=str(row['segmento']).strip(),
                cidade=str(row['cidade']).strip(),
            )
            session.add(lead)
            imported += 1

    return imported
