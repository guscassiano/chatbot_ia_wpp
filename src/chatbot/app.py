import asyncio

from fastapi import FastAPI, Request

from chatbot.buffering.message_buffer import buffer_message, debounce_tasks
from chatbot.config import BUFFER_KEY_SULFIX, NUMBER_MESSAGE_RECEIVER
from chatbot.rag.memory import get_session_history
from chatbot.redis_client import redis_client
from chatbot.services.transcription import transcribe_audio_base64
from chatbot.services.vision import analyse_image_base64
from chatbot.whatsapp.evolution_api import get_media_base64, send_wpp_message
from chatbot.whatsapp.jid_utils import mark_processed, normalize_jid

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if data.get("event") != "messages.upsert":
        return {"status": "ok"}

    key = data.get("data", {}).get("key", {})
    remote_jid = key.get("remoteJid")
    message_id = key.get("id")
    message_obj = data.get("data", {}).get("message", {})
    message_type = data.get("data", {}).get("messageType")

    message = None

    if message_type == "conversation":
        message = message_obj.get("conversation")
    elif message_type == "extendedTextMessage":
        message = message_obj.get("extendedTextMessage", {}).get("text")
    elif message_type == "audioMessage":
        base64_data = await asyncio.to_thread(get_media_base64, data.get("data"))
        if base64_data:
            message = await asyncio.to_thread(transcribe_audio_base64, base64_data)
            print(f"[AUDIO] Transcrição: {message}")
    elif message_type == "imageMessage":
        caption = message_obj.get("imageMessage", {}).get("caption", "")
        base64_data = await asyncio.to_thread(get_media_base64, data.get("data"))
        if base64_data:
            description = await asyncio.to_thread(
                analyse_image_base64, base64_data, caption
            )
            if description:
                prefix = (
                    f"[Imagem enviada pelo usuário com a legenda: '{caption}']\n"
                    if caption
                    else "[Imagem enviada]: "
                )
                message = f"{prefix}{description}"
                print(f"[IMAGE] Análise gerada: {message}")

    if not remote_jid or not message:
        return {"status": "ok"}

    chat_id = await normalize_jid(remote_jid, message_id)

    if not chat_id:
        print(
            f"[WEBHOOK] LID nao resolvido: {remote_jid} "
            f"(msg_id: {message_id}) — aguardando mensagem @s.whatsapp.net"
        )
        return {"status": "ok"}

    if not await mark_processed(message_id):
        print(f"[WEBHOOK] Mensagem duplicada ignorada: {message_id}")
        return {"status": "ok"}

    if message.strip().lower() == "/reset":
        history = get_session_history(chat_id)
        if history:
            history.clear()

        buffer_key = f"{chat_id}{BUFFER_KEY_SULFIX}"
        await redis_client.delete(buffer_key)

        if chat_id in debounce_tasks:
            debounce_tasks[chat_id].cancel()
            debounce_tasks.pop(chat_id, None)

        send_wpp_message(
            number=chat_id, text="✅ Conversa reiniciada! O histórico foi limpo."
        )

        print(f"[RESET] Histórico limpo para {chat_id}")
        return {"status": "ok"}

    if chat_id.endswith("@s.whatsapp.net"):
        if (
            not NUMBER_MESSAGE_RECEIVER
            or chat_id == f"{NUMBER_MESSAGE_RECEIVER}@s.whatsapp.net"
        ):
            await buffer_message(chat_id, message)

    return {"status": "ok"}
