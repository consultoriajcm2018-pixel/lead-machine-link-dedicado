from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func

from .classifier import QUESTIONS, QualificationState, classify, normalize_yes_no, parse_concurrent_users
from .db import session_scope
from .emailer import send_intro_email
from .messaging import get_whatsapp_client
from .models import Channel, Direction, Interaction, Lead, LeadClassification, LeadStatus


def first_message(lead: Lead) -> str:
    return (
        f'Olá, tudo bem? Aqui é da área de conectividade corporativa. '
        f'Vi que sua empresa atua com {lead.segmento} em {lead.cidade}. '
        'Posso te fazer uma pergunta rápida sobre sua internet atual?'
    )


async def process_new_leads() -> int:
    client = get_whatsapp_client()
    processed = 0
    with session_scope() as session:
        leads = session.query(Lead).filter(Lead.status == LeadStatus.NEW).all()
        for lead in leads:
            content = first_message(lead)
            await client.send_text(lead.telefone, content)
            session.add(
                Interaction(lead_id=lead.id, channel=Channel.WHATSAPP, direction=Direction.OUTBOUND, content=content)
            )
            lead.status = LeadStatus.IN_QUALIFICATION
            lead.last_interaction_at = datetime.utcnow()
            processed += 1
    return processed


async def send_email_for_in_qualification() -> int:
    sent = 0
    with session_scope() as session:
        leads = session.query(Lead).filter(Lead.status == LeadStatus.IN_QUALIFICATION).all()
        for lead in leads:
            has_email = (
                session.query(func.count(Interaction.id))
                .filter(Interaction.lead_id == lead.id, Interaction.channel == Channel.EMAIL)
                .scalar()
            )
            if has_email:
                continue
            await send_intro_email(lead.email, lead.nome_empresa, lead.segmento, lead.cidade)
            session.add(
                Interaction(
                    lead_id=lead.id,
                    channel=Channel.EMAIL,
                    direction=Direction.OUTBOUND,
                    content='E-mail introdutório enviado automaticamente.',
                )
            )
            sent += 1
    return sent


def _build_state_from_answers(answers: list[str]) -> QualificationState:
    state = QualificationState()
    if len(answers) > 0:
        state.depends_on_internet = normalize_yes_no(answers[0])
    if len(answers) > 1:
        state.uses_dedicated_link = 'dedicado' in answers[1].lower()
    if len(answers) > 2:
        state.had_instability = normalize_yes_no(answers[2])
    if len(answers) > 3:
        state.concurrent_users = parse_concurrent_users(answers[3])
    return state


def register_inbound_response(lead_id: int, message: str) -> LeadClassification | None:
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return None

        session.add(
            Interaction(lead_id=lead.id, channel=Channel.WHATSAPP, direction=Direction.INBOUND, content=message)
        )
        lead.last_interaction_at = datetime.utcnow()

        inbound_messages = (
            session.query(Interaction)
            .filter(
                Interaction.lead_id == lead.id,
                Interaction.channel == Channel.WHATSAPP,
                Interaction.direction == Direction.INBOUND,
            )
            .order_by(Interaction.created_at.asc())
            .all()
        )
        answers = [i.content for i in inbound_messages][-4:]
        if len(answers) < 4:
            lead.qualification_step = len(answers)
            return LeadClassification.UNDEFINED

        state = _build_state_from_answers(answers)
        result = classify(state)
        lead.classificacao = result

        if result == LeadClassification.HOT:
            lead.status = LeadStatus.PRIORITY
            next_text = 'Perfeito, faz sentido uma análise técnica. Qual melhor horário para uma conversa rápida?'
        elif result == LeadClassification.WARM:
            lead.status = LeadStatus.NURTURING
            next_text = 'Perfeito, vou te enviar conteúdos rápidos com boas práticas para estabilidade de internet corporativa.'
        else:
            lead.status = LeadStatus.DISCARDED
            next_text = 'Obrigado pelo retorno. Se precisar de apoio com conectividade no futuro, fico à disposição.'

        session.add(
            Interaction(lead_id=lead.id, channel=Channel.WHATSAPP, direction=Direction.OUTBOUND, content=next_text)
        )
        return result


async def process_followups() -> int:
    client = get_whatsapp_client()
    now = datetime.utcnow()
    sent = 0

    with session_scope() as session:
        leads = (
            session.query(Lead)
            .filter(Lead.status.in_([LeadStatus.IN_QUALIFICATION, LeadStatus.NURTURING]))
            .all()
        )

        for lead in leads:
            if not lead.last_interaction_at:
                continue
            elapsed = now - lead.last_interaction_at
            followup_count = (
                session.query(func.count(Interaction.id))
                .filter(
                    Interaction.lead_id == lead.id,
                    Interaction.direction == Direction.OUTBOUND,
                    Interaction.channel == Channel.WHATSAPP,
                    Interaction.content.like('Follow-up:%'),
                )
                .scalar()
            )

            content = None
            if followup_count == 0 and elapsed >= timedelta(hours=24):
                content = 'Follow-up: passando para confirmar se faz sentido conversarmos sobre estabilidade e performance da sua internet.'
            elif followup_count == 1 and elapsed >= timedelta(hours=72):
                content = 'Follow-up: último contato por aqui. Se quiser, te mostro em 10 minutos um diagnóstico técnico sem compromisso.'

            if content:
                await client.send_text(lead.telefone, content)
                session.add(
                    Interaction(
                        lead_id=lead.id,
                        channel=Channel.WHATSAPP,
                        direction=Direction.OUTBOUND,
                        content=content,
                    )
                )
                lead.last_interaction_at = now
                sent += 1

    return sent


def next_question_for_lead(lead_id: int) -> str | None:
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return None

        inbound_count = (
            session.query(func.count(Interaction.id))
            .filter(
                Interaction.lead_id == lead.id,
                Interaction.channel == Channel.WHATSAPP,
                Interaction.direction == Direction.INBOUND,
            )
            .scalar()
        )
        if inbound_count >= len(QUESTIONS):
            return None
        return QUESTIONS[inbound_count]
