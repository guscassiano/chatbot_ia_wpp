# Imagem base: python 3.11 slim (menor e mais segura que a completa)
FROM python:3.11-slim

# Boas práticas para Python em containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instala uv em uma única camada
RUN pip install --no-cache-dir --upgrade pip uv

# Copia SOMENTE os arquivos de dependência primeiro (cache de camadas)
COPY pyproject.toml uv.lock ./

# Instala dependências de produção (--frozen = usa uv.lock exato, não recalcula)
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "chatbot.app:app", "--host", "0.0.0.0", "--port", "8000"]
