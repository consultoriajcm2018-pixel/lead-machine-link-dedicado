from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func

from .db import session_scope
from .models import Direction, Interaction, Lead, LeadClassification, LeadStatus


router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/metrics')
def metrics() -> dict:
    with session_scope() as session:
        active = session.query(func.count(Lead.id)).filter(Lead.status.in_([LeadStatus.NEW, LeadStatus.IN_QUALIFICATION, LeadStatus.NURTURING, LeadStatus.PRIORITY])).scalar()
        qualified = session.query(func.count(Lead.id)).filter(Lead.classificacao == LeadClassification.HOT).scalar()
        outbound = session.query(func.count(Interaction.id)).filter(Interaction.direction == Direction.OUTBOUND).scalar() or 1
        inbound = session.query(func.count(Interaction.id)).filter(Interaction.direction == Direction.INBOUND).scalar() or 0
        response_rate = round((inbound / outbound) * 100, 2)

        return {
            'leads_ativos': active,
            'leads_qualificados': qualified,
            'taxa_resposta_percentual': response_rate,
        }
