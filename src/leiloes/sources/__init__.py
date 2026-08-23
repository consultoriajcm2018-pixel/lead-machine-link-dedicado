"""Coletores por leiloeiro. Cada modulo devolve apenas dados publicados."""

from __future__ import annotations

from . import leiloesjudiciais, megaleiloes

REGISTRY = {
    megaleiloes.SOURCE: megaleiloes,
    leiloesjudiciais.SOURCE: leiloesjudiciais,
}

__all__ = ["REGISTRY", "megaleiloes", "leiloesjudiciais"]
