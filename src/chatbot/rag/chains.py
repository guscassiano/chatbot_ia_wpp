from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.history_aware_retriever import (
    create_history_aware_retriever,
)
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from chatbot.config import (
    OPENAI_MODEL_NAME,
    OPENAI_MODEL_TEMPERATURE,
)
from chatbot.rag.memory import get_session_history
from chatbot.rag.prompts import contextualize_prompt, qa_prompt
from chatbot.rag.vectorstore import get_vectorstore

if OPENAI_MODEL_NAME is None:
    raise ValueError("OPENAI_MODEL_NAME must be set.")


def get_rag_chain():
    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        temperature=OPENAI_MODEL_TEMPERATURE,
    )
    retriever = get_vectorstore().as_retriever()
    history_aware_chain = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=qa_prompt,
    )

    return create_retrieval_chain(history_aware_chain, question_answer_chain)


def get_conversational_rag_chain():
    rag_chain = get_rag_chain()
    return RunnableWithMessageHistory(
        runnable=rag_chain,
        get_session_history=get_session_history,  # type: ignore
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
