from __future__ import annotations

from dataclasses import dataclass

from .models import LeadClassification


QUESTIONS = [
    'Sua operação depende 100% da internet?',
    'Hoje você utiliza link dedicado ou banda comum?',
    'Já teve instabilidade recente?',
    'Quantos usuários utilizam simultaneamente?',
]


@dataclass
class QualificationState:
    depends_on_internet: bool = False
    uses_dedicated_link: bool = False
    had_instability: bool = False
    concurrent_users: int = 0


def normalize_yes_no(answer: str) -> bool:
    answer = answer.lower().strip()
    yes_terms = ['sim', 'com certeza', 'depende', '100%', 'sempre']
    return any(t in answer for t in yes_terms)


def parse_concurrent_users(answer: str) -> int:
    digits = ''.join(ch for ch in answer if ch.isdigit())
    return int(digits) if digits else 0


def classify(state: QualificationState) -> LeadClassification:
    score = 0
    if state.depends_on_internet:
        score += 2
    if not state.uses_dedicated_link:
        score += 2
    if state.had_instability:
        score += 2
    if state.concurrent_users >= 20:
        score += 2
    elif state.concurrent_users >= 10:
        score += 1

    if score >= 6:
        return LeadClassification.HOT
    if score >= 3:
        return LeadClassification.WARM
    return LeadClassification.DISCARD
