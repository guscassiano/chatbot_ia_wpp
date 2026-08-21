# Chatbot IA para WhatsApp

Bot de WhatsApp com RAG (Retrieval-Augmented Generation) construído com FastAPI, LangChain e Evolution API. Recebe mensagens do WhatsApp via webhook, agrupa mensagens consecutivas com debounce, consulta uma base de conhecimento (vector store) e responde usando OpenAI.

Suporta **texto**, **áudio** (transcrição via Whisper) e **imagens** (análise via GPT-4o Vision), além de indicador de "digitando..." em tempo real e comando `/reset` para limpar o histórico de conversa.

## Funcionalidades

- **Mensagens de texto** — processadas via RAG com base de conhecimento (ChromaDB)
- **Áudios** — transcritos com OpenAI Whisper e processados como texto
- **Imagens** — analisadas com GPT-4o Vision (com ou sem legenda)
- **Indicador "digitando..."** — disparado imediatamente na chegada da mensagem, mantido ativo durante todo o processamento
- **Buffer com debounce** — agrupa mensagens consecutivas em uma única requisição
- **Comando `/reset`** — limpa histórico de conversa e buffer pendente
- **Deduplicação** — ignora mensagens duplicadas enviadas pela Evolution API
- **Normalização de LID** — resolve identificadores opacos (@lid) para JIDs reais (@s.whatsapp.net)

## Arquitetura

```
WhatsApp -> Evolution API (webhook) -> FastAPI app
                                        |
                        +---------------+---------------+
                        |               |               |
                  jid_utils      mark_processed   message_buffer
                  (normaliza       (dedup)         (debounce +
                   LID -> tel)                      agrupamento)
                                                        |
                                              +---------+---------+
                                              |                   |
                                         RAG Chain           set_typing
                                         (LangChain +      ("digitando..."
                                          OpenAI +          em background)
                                          ChromaDB)
                                              |                   |
                                              +---+---+-----------+
                                                  |
                                            evolution_api
                                            (envia resposta)

Áudio -> get_media_base64 -> Whisper (transcrição) -> message_buffer
Imagem -> get_media_base64 -> GPT-4o Vision (análise) -> message_buffer
/reset -> limpa histórico (Redis) + buffer + cancela debounce
```

## Estrutura do projeto

```
src/chatbot/
├── app.py                  # Endpoint do webhook (FastAPI) — roteamento por tipo de mensagem
├── config.py               # Carregamento de variáveis de ambiente
├── redis_client.py         # Cliente Redis compartilhado (async)
├── whatsapp/
│   ├── evolution_api.py    # Envio de mensagens, presença (typing) e download de mídia (base64)
│   └── jid_utils.py        # Normalização de JID (LID -> @s.whatsapp.net) + dedup
├── buffering/
│   └── message_buffer.py   # Debounce, agrupamento de mensagens e indicador de digitação
├── services/
│   ├── transcription.py    # Transcrição de áudio via OpenAI Whisper
│   └── vision.py           # Análise de imagens via GPT-4o Vision
└── rag/
    ├── chains.py           # Construção da RAG chain (LangChain)
    ├── memory.py           # Histórico de conversa (Redis)
    ├── prompts.py          # Templates de prompt (sistema + contextualização)
    └── vectorstore.py      # Indexação de documentos (ChromaDB + OpenAI Embeddings)
```

## Pré-requisitos

- Docker e Docker Compose
- Uma instância do WhatsApp configurada na Evolution API
- Chave de API da OpenAI

## Configuração

1. Clone o repositório e crie o arquivo `.env` na raiz a partir do template:

```bash
cp .env.example .env
```

Depois edite o `.env` preenchendo suas credenciais. As variáveis estão agrupadas por seção (OpenAI, RAG, Evolution API, Redis e Buffer) com comentários explicativos no próprio arquivo.

```env
# OpenAI
OPENAI_API_KEY=sua-chave-aqui
OPENAI_MODEL_NAME=gpt-4o-mini
OPENAI_MODEL_TEMPERATURE=0.7

# Prompts da IA
IA_CONTEXTUALIZE_PROMPT="Dado o historico da conversa, reformule a pergunta para ser independente de contexto."
IA_SYSTEM_PROMPT="Voce e um assistente que responde com base nos documentos fornecidos."

# RAG
VECTOR_STORE_PATH=/app/vectorstore
RAG_FILES_DIR=/app/rag_files

# Evolution API
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_INSTANCE_NAME=sua-instancia
AUTHENTICATION_API_KEY=sua-apikey-evolution

# Redis
CACHE_REDIS_URI=redis://redis:6379/6

# Buffer
BUFFER_KEY_SULFIX=_msg_buffer
DEBOUNCE_SECONDS=10
BUFFER_TTL=300

# Número autorizado a interagir com o bot (com DDD e código do país, sem +)
NUMBER_MESSAGE_RECEIVER=5535999999999

# Evolution API — workaround para QR Code (issue #2437)
CONFIG_SESSION_PHONE_VERSION=2.3000.1033773198
CACHE_REDIS_ENABLED=false
CACHE_LOCAL_ENABLED=true
DATABASE_SAVE_DATA_CHATS=false
DATABASE_SAVE_DATA_CONTACTS=false
DATABASE_SAVE_DATA_HISTORIC=false
DATABASE_SAVE_DATA_LABELS=false
```

2. Suba os containers:

```bash
docker compose up -d
```

3. Crie a instância na Evolution API e escaneie o QR Code:

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "Content-Type: application/json" \
  -H "apikey: sua-apikey-global" \
  -d '{"instanceName": "sua-instancia", "qrcode": true, "integration": "WHATSAPP-BAILEYS"}'
```

4. Configure o webhook para apontar para o bot:

```bash
curl -X POST http://localhost:8080/webhook/set/sua-instancia \
  -H "Content-Type: application/json" \
  -H "apikey: seu-token" \
  -d '{"webhook": {"enabled": true, "url": "http://bot:8000/webhook", "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]}}'
```

5. Adicione documentos à base de conhecimento em `rag_files/` e reinicie o bot para indexá-los.

## Uso

- Envie **texto** para conversar com o bot
- Envie **áudio** — ele transcreve e responde como se fosse texto
- Envie **imagem** (com ou sem legenda) — ele analisa e descreve o conteúdo
- Digite **`/reset`** para limpar o histórico de conversa

## Como funciona

### Fluxo de mensagens

1. O usuário envia uma mensagem (texto, áudio ou imagem) no WhatsApp
2. A Evolution API dispara o webhook para o bot (FastAPI)
3. O bot normaliza o JID, verifica duplicação e identifica o tipo de mensagem
4. **Texto** vai direto para o buffer; **áudio** é transcrito via Whisper; **imagem** é analisada via GPT-4o Vision
5. O indicador "digitando..." é disparado imediatamente em background (thread separada, não bloqueia o event loop)
6. Após o debounce, as mensagens agrupadas são enviadas para a RAG chain
7. A resposta é enviada de volta via Evolution API

### Normalização de JID (`jid_utils.py`)

A Evolution API pode enviar mensagens com `@lid` (identificador opaco) em vez de `@s.whatsapp.net` (que contem o numero de telefone). O `normalize_jid` resolve o LID para o JID real usando um mapa no Redis (TTL de 7 dias). Se nao conseguir resolver, aguarda mensagens futuras do mesmo remetente que tragam o JID correto.

### Deduplicação (`jid_utils.py`)

A Evolution API pode enviar a mesma mensagem mais de uma vez (retry de entrega). O `mark_processed` usa `SET ... NX` no Redis (TTL de 5 minutos) para garantir que cada mensagem seja processada apenas uma vez.

### Buffer com debounce (`message_buffer.py`)

Quando o usuario envia varias mensagens seguidas (ex: "Por favor", "Me de as dicas"), o bot espera `DEBOUNCE_SECONDS` e agrupa tudo em uma unica mensagem antes de enviar para a IA. Cada nova mensagem reseta o timer. As mensagens ficam armazenadas no Redis durante o debounce.

### Indicador "digitando..." (`evolution_api.py` + `message_buffer.py`)

Assim que a primeira mensagem chega, o bot dispara `set_typing(presence="composing")` em uma thread separada (`asyncio.to_thread`), configurando um `delay` na Evolution API que mantém o status ativo. Isso não bloqueia o event loop do FastAPI — o debounce e o processamento da IA rodam normalmente enquanto o "digitando..." aparece no WhatsApp do usuário.

### Áudio (`services/transcription.py`)

1. O webhook identifica `messageType == "audioMessage"`
2. A função `get_media_base64` baixa o áudio da Evolution API em formato base64
3. O base64 é decodificado e enviado para a API do Whisper (`openai.audio.transcriptions.create`)
4. O texto transcrito é repassado para o `buffer_message` como se fosse uma mensagem de texto normal

### Imagem (`services/vision.py`)

1. O webhook identifica `messageType == "imageMessage"`
2. A função `get_media_base64` baixa a imagem da Evolution API em formato base64
3. A imagem é enviada para o GPT-4o junto com a legenda (se houver) ou um prompt padrão de descrição
4. A análise é repassada para o `buffer_message` como contexto para a IA responder

### Comando `/reset`

Quando o usuário envia `/reset`, o bot:
1. Limpa o histórico de conversa no Redis (`RedisChatMessageHistory.clear()`)
2. Remove mensagens pendentes do buffer
3. Cancela qualquer debounce em andamento
4. Responde com uma confirmação

### RAG (`rag/`)

1. Documentos em `rag_files/` sao carregados, divididos em chunks e indexados no ChromaDB (`vectorstore.py`)
2. A chain consulta a base de conhecimento relevante + historico de conversa (`chains.py`, `memory.py`)
3. A resposta e gerada pelo modelo da OpenAI usando os prompts configurados (`prompts.py`)

### Envio de resposta (`evolution_api.py`)

A resposta da IA e enviada de volta para o usuario via endpoint `sendText` da Evolution API.

## Variaveis do Redis

| Chave | TTL | Descricao |
|---|---|---|
| `lid_map:{jid}` | 7 dias | Mapa LID -> JID com telefone |
| `msg_jid:{message_id}` | 120s | JID temporario por mensagem |
| `processed:{message_id}` | 300s | Deduplicacao de mensagens |
| `{chat_id}_msg_buffer` | 300s | Buffer de mensagens durante debounce |

### Inspecionar o Redis

O bot usa o database 6 do Redis. Para inspecionar:

```bash
# Listar todas as chaves
docker exec redis redis-cli -n 6 KEYS '*'

# Ver valor de uma chave
docker exec redis redis-cli -n 6 GET 'lid_map:xxx@lid'

# Ver TTL de uma chave
docker exec redis redis-cli -n 6 TTL 'lid_map:xxx@lid'
```

## Stack

- **FastAPI** — framework web
- **LangChain** + **OpenAI** (GPT-4o + Whisper) — RAG, LLM, visão e transcrição de áudio
- **ChromaDB** — vector store
- **Redis** — cache, dedup, buffer e historico de conversa
- **Evolution API v2.3.7** — ponte para WhatsApp
- **Postgres** — persistencia da Evolution API
- **Docker Compose** — orquestracao
- **uv** — gerenciador de dependencias
