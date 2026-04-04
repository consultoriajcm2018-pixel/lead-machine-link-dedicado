from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, Enum):
    NEW = 'NEW'
    IN_QUALIFICATION = 'IN_QUALIFICATION'
    NURTURING = 'NURTURING'
    PRIORITY = 'PRIORITY'
    DISCARDED = 'DISCARDED'
    CLOSED_WON = 'CLOSED_WON'
    CLOSED_LOST = 'CLOSED_LOST'


class LeadClassification(str, Enum):
    UNDEFINED = 'UNDEFINED'
    HOT = 'LEAD_QUENTE'
    WARM = 'LEAD_MORNO'
    DISCARD = 'DESCARTAR'


class Channel(str, Enum):
    WHATSAPP = 'WHATSAPP'
    EMAIL = 'EMAIL'
    SYSTEM = 'SYSTEM'


class Direction(str, Enum):
    OUTBOUND = 'OUTBOUND'
    INBOUND = 'INBOUND'


class Lead(Base):
    __tablename__ = 'leads'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_empresa: Mapped[str] = mapped_column(String(200), nullable=False)
    telefone: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    segmento: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)

    status: Mapped[LeadStatus] = mapped_column(SAEnum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    classificacao: Mapped[LeadClassification] = mapped_column(
        SAEnum(LeadClassification), default=LeadClassification.UNDEFINED, nullable=False
    )
    qualification_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    interactions: Mapped[list['Interaction']] = relationship(back_populates='lead', cascade='all, delete-orphan')


class Interaction(Base):
    __tablename__ = 'interactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey('leads.id'), nullable=False, index=True)
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel), nullable=False)
    direction: Mapped[Direction] = mapped_column(SAEnum(Direction), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    lead: Mapped[Lead] = relationship(back_populates='interactions')
