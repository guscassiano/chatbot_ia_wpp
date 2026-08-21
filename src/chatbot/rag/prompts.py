from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from chatbot.config import (
    IA_CONTEXTUALIZE_PROMPT,
    IA_SYSTEM_PROMPT,
)

if IA_CONTEXTUALIZE_PROMPT is None or IA_SYSTEM_PROMPT is None:
    raise ValueError("IA_CONTEXTUALIZE_PROMPT and IA_SYSTEM_PROMPT must be set.")

contextualize_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", IA_CONTEXTUALIZE_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", IA_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)
