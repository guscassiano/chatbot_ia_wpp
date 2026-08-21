from langchain_community.chat_message_histories import RedisChatMessageHistory

from chatbot.config import REDIS_URL


def get_session_history(session_id):
    if REDIS_URL:
        return RedisChatMessageHistory(
            session_id=session_id,
            url=REDIS_URL,
        )
