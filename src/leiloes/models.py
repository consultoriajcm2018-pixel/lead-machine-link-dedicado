"""Estrutura de um lote. Todo campo vem da pagina de origem ou fica vazio."""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any


@dataclasses.dataclass(slots=True)
class Lote:
    source: str
    source_id: str
    url: str
    title: str

    price: float | None = None
    appraisal: float | None = None
    discount_label: str = ""
    discount_pct: int | None = None

    city: str = ""
    uf: str = ""
    modality: str = ""          # Judicial / Extrajudicial, conforme a origem
    lot_number: str = ""
    status: str = ""
    first_date: str = ""
    second_date: str = ""
    image_url: str = ""
    year_label: str = ""
    model_year: int | None = None   # ano modelo declarado; None = nao declarado

    body: str = ""              # suv | picape | outro | nao_carro
    tier: str | None = None     # premium | intermediario
    sunroof: bool | None = None  # None = a origem nao informou
    payment_terms: str = ""      # o que o anuncio diz sobre parcelamento
    scrap: bool = False          # anuncio classifica como sucata/incompleto
    rights_only: bool = False    # lote e o direito sobre o bem, nao o bem
    description: str = ""

    fetched_at: str = dataclasses.field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    )

    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
