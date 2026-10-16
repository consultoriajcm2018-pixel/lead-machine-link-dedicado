"""Leitura do ano/modelo declarado no anuncio.

No Brasil o leiloeiro escreve ano de fabricacao/ano modelo, as vezes com
quatro digitos ("2019/2020"), as vezes com dois ("19/20"). Vale o ano
modelo - o segundo. Quando o anuncio nao declara ano, o resultado e None:
idade nao se estima por aparencia nem por geracao do modelo.

Fora do titulo o texto esta cheio de numero com cara de ano que nao e ano do
carro - numero de processo ("0001046-71.2023.5.07.0010"), data de praca,
endereco. Por isso a descricao do lote so e aceita quando o ano vem rotulado
("Ano/Modelo 2008/2009"), nunca solto.
"""

from __future__ import annotations

import datetime as dt
import re

_PAR_LONGO = re.compile(r"\b((?:19|20)\d{2})\s*/\s*((?:19|20)?\d{2})\b")
_PAR_CURTO = re.compile(r"(?<![\d/.-])(\d{2})\s*/\s*(\d{2})(?![\d/.-])")
_SOLTO = re.compile(r"(?<![\d.-])((?:19|20)\d{2})(?![\d.-])")

# "Ano/Modelo 2008/2009", "ANO FAB/MOD: 2019/2020", "Ano: 2013"
_ROTULO = re.compile(
    r"\bano\s*(?:de\s*)?(?:fabrica\w*|fab\.?)?\s*[/e]?\s*(modelo|mod\.?)?\s*:?\s*"
    r"((?:19|20)?\d{2}\s*/\s*(?:19|20)?\d{2}|(?:19|20)\d{2})",
    re.I,
)


def _expandir(dois_digitos: int, referencia: int) -> int:
    """'23' -> 2023; '60' -> 1960. Ano futuro vira o seculo anterior."""
    candidato = 2000 + dois_digitos
    # Montadora emplaca modelo do ano seguinte, entao aceita +1 ano.
    return candidato if candidato <= referencia + 1 else 1900 + dois_digitos


def _do_par(trecho: str, referencia: int) -> int | None:
    longo = _PAR_LONGO.search(trecho)
    if longo:
        primeiro = int(longo.group(1))
        segundo = longo.group(2)
        ano = int(segundo) if len(segundo) == 4 else _expandir(int(segundo), referencia)
        return max(ano, primeiro)
    curto = _PAR_CURTO.search(trecho)
    if curto:
        return max(_expandir(int(curto.group(1)), referencia),
                   _expandir(int(curto.group(2)), referencia))
    return None


def _do_rotulo(texto: str, referencia: int) -> int | None:
    for achado in _ROTULO.finditer(texto):
        rotulo_modelo, valor = achado.group(1), achado.group(2)
        par = _do_par(valor, referencia)
        if par:
            return par
        # Ano sozinho so vale quando o rotulo fala em modelo; "no ano de 2023"
        # dentro de um texto de edital nao e ano do veiculo.
        if rotulo_modelo:
            return int(valor)
    return None


def parse_model_year(
    *textos: str,
    referencia: int | None = None,
    somente_rotulado: bool = False,
) -> int | None:
    """Ano modelo declarado, ou None quando o anuncio nao diz.

    `somente_rotulado=True` para textos longos (descricao do lote), onde um
    numero com cara de ano quase sempre e processo ou data de praca.
    """
    referencia = referencia or dt.date.today().year
    for texto in textos:
        if not texto:
            continue
        ano = _do_rotulo(texto, referencia)
        if ano:
            return ano
        if somente_rotulado:
            continue
        ano = _do_par(texto, referencia)
        if ano:
            return ano
        solto = _SOLTO.search(texto)
        if solto:
            return int(solto.group(1))
    return None


def idade(ano_modelo: int | None, referencia: int | None = None) -> int | None:
    """Anos de uso contados do ano modelo. None quando o ano nao foi declarado."""
    if ano_modelo is None:
        return None
    return max(0, (referencia or dt.date.today().year) - ano_modelo)
