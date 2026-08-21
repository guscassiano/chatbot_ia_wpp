import asyncio
import logging

import requests

from chatbot.config import (
    EVOLUTION_API_URL,
    EVOLUTION_AUTHENTICATION_API_KEY,
    EVOLUTION_INSTANCE_NAME,
)

logger = logging.getLogger(__name__)


def send_wpp_message(number, text):
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
    }
    payload = {"number": number, "text": text}

    try:
        response = requests.post(url=url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        logger.info("Mensagem enviada para %s: %s", number, response.json())
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao enviar mensagem para %s: %s", number, e)


def set_typing(number, presence):
    url = f"{EVOLUTION_API_URL}/chat/sendPresence/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
    }
    payload = {"number": number, "delay": 30000, "presence": presence}

    try:
        response = requests.post(url=url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Digitando enviado para {number}")
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao enviar mensagem digitando para %s: %s", number, e)


def get_media_base64(message_data: dict) -> str | None:
    url = (
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}"
    )
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
    }
    payload = {
        "message": message_data,
        "convertToMp4": False,
    }

    try:
        response = requests.post(url=url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data.get("base64")
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao obter base64 da mídia: %s", e)
        return None
