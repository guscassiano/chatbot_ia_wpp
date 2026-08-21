import base64

from openai import OpenAI

from chatbot.config import OPENAI_API_KEY, OPENAI_MODEL_NAME

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def analyse_image_base64(
    image_base64: str, user_prompt: str | None = None
) -> str | None:
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        prompt_text = (
            user_prompt
            if user_prompt and user_prompt.strip()
            else (
                "Descreva e analise detalhadamente oconteúdo desta imagem em português de forma concisa e clara."
            )
        )

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL_NAME or "gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_completion_tokens=500,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[VISION ERROR] Falha ao analisar a imagem: {e}")
        return None
