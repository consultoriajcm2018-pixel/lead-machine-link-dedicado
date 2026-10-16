"""Coletor do Mega Leiloes (https://www.megaleiloes.com.br).

Le as paginas publicas de listagem de veiculos e converte cada card em um
Lote. Nada e completado por estimativa: campo ausente na pagina fica vazio.
"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from ..anos import parse_model_year
from ..catalog import classify_body, has_sunroof, suv_tier
from ..extract import forma_pagamento, is_sucata, so_direitos
from ..http import get_text
from ..models import Lote

SOURCE = "megaleiloes"
SOURCE_LABEL = "Mega Leiloes"
BASE = "https://www.megaleiloes.com.br"

CATEGORIES = ("carros", "caminhoes")

_MONEY = re.compile(r"R\$\s*([\d.]+),(\d{2})")
_PCT = re.compile(r"(\d{1,3})\s*%")
_YEAR = re.compile(r"\b((?:19|20)\d{2})(?:\s*/\s*(?:19|20)?\d{2})?\b")


def parse_money(text: str) -> float | None:
    match = _MONEY.search(text or "")
    if not match:
        return None
    return float(match.group(1).replace(".", "") + "." + match.group(2))


def _text(node, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def parse_card(card) -> Lote | None:
    link = card.select_one("a.card-title")
    if not link:
        return None
    url = (link.get("href") or "").split("?")[0]
    title = link.get_text(" ", strip=True)
    if not url or not title:
        return None

    lot_id = _text(card, ".card-number") or url.rsplit("-", 1)[-1]

    locality = _text(card, ".card-locality")
    city, _, uf = locality.partition(",")

    discount_label = " ".join(_text(card, ".card-down").split())
    pct = _PCT.search(discount_label)

    year = _YEAR.search(title)

    image = card.select_one("a.card-image")
    image_url = (image.get("data-bg") or "") if image else ""
    if "card-no-image" in image_url:
        image_url = ""

    lote = Lote(
        source=SOURCE,
        source_id=lot_id.strip(),
        url=url,
        title=title,
        price=parse_money(_text(card, ".card-price")),
        discount_label=discount_label,
        discount_pct=int(pct.group(1)) if pct else None,
        city=city.strip(),
        uf=uf.strip(),
        modality=_text(card, ".card-instance-title a"),
        lot_number=_text(card, ".card-batch-number"),
        status=_text(card, ".card-status"),
        first_date=_text(card, ".card-first-instance-date").replace("1ª Praça:", "").strip(),
        second_date=_text(card, ".card-second-instance-date").replace("2ª Praça:", "").strip(),
        image_url=image_url,
        year_label=year.group(0) if year else "",
    )
    lote.body = classify_body(title)
    lote.tier = suv_tier(title)
    lote.sunroof = True if has_sunroof(title) else None
    lote.model_year = parse_model_year(title)
    lote.scrap = is_sucata(title)
    lote.rights_only = so_direitos(title)
    return lote


def parse_listing(html: str) -> list[Lote]:
    soup = BeautifulSoup(html, "lxml")
    lotes = []
    for card in soup.select("div.card"):
        lote = parse_card(card)
        if lote is not None:
            lotes.append(lote)
    return lotes


def collect(client: httpx.Client, max_pages: int = 6) -> list[Lote]:
    """Percorre as categorias de veiculos e devolve os lotes publicados."""
    seen: set[str] = set()
    result: list[Lote] = []
    for category in CATEGORIES:
        for page in range(1, max_pages + 1):
            html = get_text(client, f"{BASE}/veiculos/{category}?pagina={page}")
            if not html:
                break
            lotes = parse_listing(html)
            if not lotes:
                break
            new = 0
            for lote in lotes:
                if lote.key() in seen:
                    continue
                seen.add(lote.key())
                result.append(lote)
                new += 1
            if new == 0:
                break
    return result


def enrich(client: httpx.Client, lote: Lote) -> Lote:
    """Abre a pagina do lote para ler descricao, avaliacao e teto solar."""
    html = get_text(client, lote.url, retries=2)
    if not html:
        return lote
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    body = soup.select_one(".batch-description, .batch-content, main") or soup
    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
    lote.description = text[:4000]
    if has_sunroof(text):
        lote.sunroof = True
    if lote.model_year is None:
        lote.model_year = parse_model_year(text, somente_rotulado=True)
    lote.payment_terms = forma_pagamento(text)
    lote.scrap = lote.scrap or is_sucata(text)
    lote.rights_only = lote.rights_only or so_direitos(text)
    for label in ("Valor de avalia", "Avalia"):
        idx = text.find(label)
        if idx != -1:
            value = parse_money(text[idx: idx + 120])
            if value:
                lote.appraisal = value
                break
    return lote
