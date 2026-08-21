from chatbot.redis_client import redis_client

LID_MAP_TTL = 7 * 24 * 3600
MSG_ID_TTL = 120
PROCESSED_TTL = 300


async def normalize_jid(remote_jid: str, message_id: str) -> str | None:
    if remote_jid.endswith("@s.whatsapp.net"):
        await redis_client.set(f"msg_jid:{message_id}", remote_jid, ex=MSG_ID_TTL)
        return remote_jid

    if remote_jid.endswith("@lid"):
        phone_jid = await redis_client.get(f"lid_map:{remote_jid}")
        print(f"Se foi mapeado: {phone_jid}")
        if phone_jid:
            assert isinstance(phone_jid, str)
            return phone_jid

        phone_jid = await redis_client.get(f"msg_jid:{message_id}")
        print(f"Se não foi mapeado: {phone_jid}")
        if phone_jid:
            assert isinstance(phone_jid, str)
            await redis_client.set(f"lid_map:{remote_jid}", phone_jid, ex=LID_MAP_TTL)
            return phone_jid

        return None

    return remote_jid


async def mark_processed(message_id: str) -> bool:
    result = await redis_client.set(
        f"processed:{message_id}", "1", ex=PROCESSED_TTL, nx=True
    )
    return result is not None
