"""Leitura de condicoes declaradas no anuncio do lote.

Cada funcao devolve apenas o que o texto da origem afirma. Quando o anuncio
nao diz nada, o resultado e vazio/None - nunca um palpite.
"""

from __future__ import annotations

from .catalog import norm

_SO_A_VISTA = (
    "a vista (integral em parcela unica)",
    "pagamento a vista (integral",
    "somente a vista",
    "exclusivamente a vista",
    "pagamento integral em parcela unica",
)

_PARCELADO = (
    "proposta parcelada",
    "parcelamento",
    "parcelada em ate",
    "pagamento parcelado",
    "art. 895",
    "artigo 895",
)

_SUCATA = (
    "sucata",
    "motor inservivel",
    "inservivel",
    "somente lataria",
    "so a lataria",
    "carcaca",
    "monobloco",
    "sinistrado",
    "incendiado",
)


def forma_pagamento(*textos: str) -> str:
    """'somente a vista' | 'aceita proposta parcelada' | '' (nao declarado)."""
    blob = norm(" ".join(t for t in textos if t))
    if not blob:
        return ""
    tem_parcelamento = any(marca in blob for marca in _PARCELADO)
    if any(marca in blob for marca in _SO_A_VISTA) and not tem_parcelamento:
        return "somente a vista"
    if tem_parcelamento:
        return "aceita proposta parcelada"
    return ""


def is_sucata(*textos: str) -> bool:
    """True quando o proprio anuncio classifica o bem como sucata/incompleto."""
    blob = norm(" ".join(t for t in textos if t))
    return any(marca in blob for marca in _SUCATA)


def so_direitos(*textos: str) -> bool:
    """True quando o lote e o direito sobre o bem, nao o bem em si."""
    blob = norm(" ".join(t for t in textos if t))
    return "direitos sobre" in blob or "direitos aquisitivos" in blob or blob.startswith("direito -")
