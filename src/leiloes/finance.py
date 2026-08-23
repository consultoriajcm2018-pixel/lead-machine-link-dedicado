"""Simulacao de pagamento parcelado em leilao judicial.

Base legal: Lei 13.105/2015 (Codigo de Processo Civil), art. 895.

  - inciso II: o interessado pode apresentar proposta de pagamento do
    restante em ate 30 (trinta) meses;
  - paragrafo 1o: a proposta deve conter, em qualquer hipotese, oferta de
    pagamento de pelo menos 25% (vinte e cinco por cento) do valor do lance
    a vista, e o restante parcelado;
  - paragrafo 2o: as prestacoes sao mensais e sucessivas, corrigidas
    monetariamente;
  - paragrafo 7o: a proposta parcelada nao suspende o leilao e so prevalece
    sobre a proposta a vista se o juiz assim decidir.

Consequencia pratica: entrada de 0% nao existe nessa modalidade. O minimo
legal e 25%. A parcela nao tem juros, mas tem correcao monetaria.
"""

from __future__ import annotations

import dataclasses

MIN_ENTRADA_PCT = 0.25
MAX_PARCELAS = 30

# Percentual usual da comissao do leiloeiro, cobrado a vista sobre o valor da
# arrematacao. O valor real de cada leilao esta no edital do lote.
COMISSAO_LEILOEIRO_PCT_USUAL = 0.05


class RegraLegalError(ValueError):
    """Parametro que a lei nao permite."""


@dataclasses.dataclass(slots=True)
class Simulacao:
    valor_lance: float
    entrada_pct: float
    parcelas: int
    entrada: float
    parcela: float
    total_parcelado: float
    comissao_leiloeiro: float
    desembolso_inicial: float
    observacoes: list[str]


def simular(
    valor_lance: float,
    entrada_pct: float = MIN_ENTRADA_PCT,
    parcelas: int = MAX_PARCELAS,
    comissao_pct: float = COMISSAO_LEILOEIRO_PCT_USUAL,
) -> Simulacao:
    if valor_lance <= 0:
        raise RegraLegalError("Valor do lance deve ser positivo.")
    if entrada_pct < MIN_ENTRADA_PCT:
        raise RegraLegalError(
            "O art. 895, par. 1o, do CPC exige no minimo 25% de entrada a vista. "
            "Nao existe parcelamento judicial com entrada zero."
        )
    if entrada_pct > 1:
        raise RegraLegalError("Entrada nao pode passar de 100%.")
    if not 1 <= parcelas <= MAX_PARCELAS:
        raise RegraLegalError("O art. 895, II, do CPC limita o parcelamento a 30 meses.")

    entrada = round(valor_lance * entrada_pct, 2)
    saldo = round(valor_lance - entrada, 2)
    parcela = round(saldo / parcelas, 2) if saldo else 0.0
    comissao = round(valor_lance * comissao_pct, 2)

    observacoes = [
        "Parcelas sem juros, mas corrigidas monetariamente (art. 895, par. 2o).",
        f"Comissao do leiloeiro ({comissao_pct:.0%}) costuma ser paga a vista, fora do parcelamento; confira o edital.",
        "Sobre moveis, a proposta parcelada exige caucao idonea (art. 895, par. 1o).",
        "Debitos de IPVA, multas e transferencia dependem do que o edital do lote diz.",
        "Proposta parcelada pode perder para uma proposta a vista (art. 895, par. 7o).",
    ]

    return Simulacao(
        valor_lance=round(valor_lance, 2),
        entrada_pct=entrada_pct,
        parcelas=parcelas,
        entrada=entrada,
        parcela=parcela,
        total_parcelado=saldo,
        comissao_leiloeiro=comissao,
        desembolso_inicial=round(entrada + comissao, 2),
        observacoes=observacoes,
    )
