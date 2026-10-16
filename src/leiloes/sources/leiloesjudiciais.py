"""Coletor do Leiloes Judiciais (https://www.leiloesjudiciais.com.br).

Le as paginas publicas de veiculos. Como a origem publica avaliacao e lance
atual separadamente, os dois campos sao guardados como vem.
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

SOURCE = "leiloesjudiciais"
SOURCE_LABEL = "Leiloes Judiciais"
BASE = "https://www.leiloesjudiciais.com.br"

CATEGORIES = ("carros",)

_MONEY = re.compile(r"R\$\s*([\d.]+),(\d{2})")
_YEAR = re.compile(r"\b((?:19|20)\d{2})(?:\s*/\s*(?:19|20)?\d{2})?\b")


def parse_money(text: str) -> float | None:
    match = _MONEY.search(text or "")
    if not match:
        return None
    return float(match.group(1).replace(".", "") + "." + match.group(2))


def _valores(card) -> dict[str, float | None]:
    valores: dict[str, float | None] = {}
    for bloco in card.select(".label-valor"):
        spans = bloco.find_all("span")
        if len(spans) >= 2:
            rotulo = spans[0].get_text(strip=True).lower()
            valores[rotulo] = parse_money(spans[1].get_text(strip=True))
    return valores


def parse_card(card) -> Lote | None:
    link = card.select_one("a.card-lote-leilao")
    header = card.select_one(".card-header span")
    if not link or not header:
        return None
    href = link.get("href") or ""
    title = header.get_text(" ", strip=True)
    if not href or not title:
        return None

    url = href if href.startswith("http") else BASE + href
    source_id = href.strip("/").split("/")[-1]

    valores = _valores(card)
    avaliacao = valores.get("avaliação") or valores.get("avaliacao")
    lance = valores.get("lance atual") or valores.get("lance inicial")

    localidade = card.select_one(".cidade-estado span")
    cidade_uf = localidade.get_text(strip=True) if localidade else ""
    city, _, uf = cidade_uf.partition("/")

    status = card.select_one(".status span")
    numero = card.select_one(".numero-lote")
    imagem = card.select_one("img.imagem__lote")
    ano = _YEAR.search(title)

    desconto = None
    if avaliacao and lance and avaliacao > 0 and lance < avaliacao:
        desconto = int(round((1 - lance / avaliacao) * 100))

    lote = Lote(
        source=SOURCE,
        source_id=source_id,
        url=url,
        title=title,
        price=lance if lance else avaliacao,
        appraisal=avaliacao,
        discount_pct=desconto,
        discount_label=f"{desconto}% abaixo da avaliacao" if desconto else "",
        city=city.strip(),
        uf=uf.strip(),
        modality="Judicial",
        lot_number=numero.get_text(strip=True) if numero else "",
        status=status.get_text(strip=True) if status else "",
        image_url=(imagem.get("src") or "") if imagem else "",
        year_label=ano.group(0) if ano else "",
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
    for card in soup.select(".base-card"):
        lote = parse_card(card)
        if lote is not None:
            lotes.append(lote)
    return lotes


def collect(client: httpx.Client, max_pages: int = 6) -> list[Lote]:
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
    html = get_text(client, lote.url, retries=2)
    if not html:
        return lote
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "svg"]):
        tag.decompose()
    main = soup.select_one("main") or soup
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    lote.description = text[:4000]
    if has_sunroof(text):
        lote.sunroof = True
    if lote.model_year is None:
        lote.model_year = parse_model_year(text, somente_rotulado=True)
    lote.payment_terms = forma_pagamento(text)
    lote.scrap = lote.scrap or is_sucata(text)
    lote.rights_only = lote.rights_only or so_direitos(text)
    return lote
