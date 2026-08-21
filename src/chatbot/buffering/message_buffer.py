import asyncio

from chatbot.config import (
    BUFFER_KEY_SULFIX,
    BUFFER_TTL,
    DEBOUNCE_SECONDS,
    NUMBER_MESSAGE_RECEIVER,
)
from chatbot.rag.chains import get_conversational_rag_chain
from chatbot.redis_client import redis_client
from chatbot.whatsapp.evolution_api import (
    send_wpp_message,
    set_typing,
)

conversational_rag_chain = get_conversational_rag_chain()
debounce_tasks: dict[str, asyncio.Task] = {}
typing_tasks: dict[str, asyncio.Task] = {}


def log(*args):
    print("[BUFFER] ", *args)


async def buffer_message(chat_id: str, message: str):
    buffer_key = f"{chat_id}{BUFFER_KEY_SULFIX}"

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL)

    log(f"Mensagem adicionada ao buffer de {chat_id}: {message}")

    asyncio.create_task(asyncio.to_thread(set_typing, chat_id, "composing"))

    if debounce_tasks.get(chat_id):
        debounce_tasks[chat_id].cancel()
        log(f"Debounce resetado para {chat_id}")

    debounce_tasks[chat_id] = asyncio.create_task(handle_debounce(chat_id))


async def handle_debounce(chat_id: str):
    try:
        log(f"Iniciando debounce para {chat_id}")
        await asyncio.sleep(DEBOUNCE_SECONDS)

        buffer_key = f"{chat_id}{BUFFER_KEY_SULFIX}"
        messages = await redis_client.lrange(buffer_key, 0, -1)

        full_message = " ".join(messages).strip()  # type: ignore

        if full_message:
            log(f"Enviando mesagem agrupada para {chat_id}: {full_message}")

            ai_response = conversational_rag_chain.invoke(
                input={"input": full_message},
                config={"configurable": {"session_id": chat_id}},
            )["answer"]

            send_wpp_message(
                number=chat_id,
                text=ai_response,
            )

        await redis_client.delete(buffer_key)

    except asyncio.CancelledError:
        log(f"Debounce cancelado para {chat_id}")
