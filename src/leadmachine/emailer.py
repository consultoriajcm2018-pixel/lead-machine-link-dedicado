from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from .config import settings


async def send_intro_email(to_email: str, company_name: str, segmento: str, cidade: str) -> None:
    message = EmailMessage()
    message['From'] = settings.smtp_from
    message['To'] = to_email
    message['Subject'] = f'Conectividade corporativa para {company_name}'
    message.set_content(
        (
            f'Olá, equipe da {company_name}.\n\n'
            f'Somos especialistas em link dedicado para operações de {segmento} em {cidade}. '
            'Podemos propor uma análise técnica rápida para melhorar estabilidade e desempenho.\n\n'
            'Se fizer sentido, responda este e-mail com o melhor horário.\n\n'
            'Abraços.'
        )
    )

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_pass,
        start_tls=True,
    )
