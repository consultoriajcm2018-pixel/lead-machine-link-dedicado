from __future__ import annotations

import asyncio
import random

import httpx

from .config import settings


class WhatsAppClient:
    async def send_text(self, phone: str, text: str) -> None:
        raise NotImplementedError


class EvolutionWhatsAppClient(WhatsAppClient):
    async def send_text(self, phone: str, text: str) -> None:
        delay = random.randint(settings.message_min_delay_seconds, settings.message_max_delay_seconds)
        await asyncio.sleep(delay)
        url = f"{settings.evolution_api_url.rstrip('/')}/message/sendText/{settings.evolution_instance}"
        headers = {'apikey': settings.evolution_api_key, 'Content-Type': 'application/json'}
        payload = {'number': phone, 'text': text}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()


def get_whatsapp_client() -> WhatsAppClient:
    return EvolutionWhatsAppClient()
