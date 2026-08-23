"""Cliente HTTP compartilhado pelos coletores."""

from __future__ import annotations

import time

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def build_client(timeout: float = 30.0) -> httpx.Client:
    return httpx.Client(
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        follow_redirects=True,
    )


def get_text(client: httpx.Client, url: str, retries: int = 3) -> str | None:
    """Baixa uma pagina. Devolve None quando a origem nao responde 200.

    Nunca levanta excecao para o chamador: uma origem fora do ar deve
    reduzir o resultado, nunca inventar conteudo.
    """
    delay = 2.0
    for attempt in range(retries):
        try:
            response = client.get(url)
        except httpx.HTTPError:
            response = None
        if response is not None and response.status_code == 200:
            return response.text
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    return None
