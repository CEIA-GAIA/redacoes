# Dockerfile — Pipeline GPT OSS / OpenAI / Gemini Correção Redações

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependências primeiro (cache eficiente)
COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar código do projeto
COPY main.py .

# Variáveis default (podem ser sobrescritas no runtime)
# ENV LLM_PROVIDER=openai
ENV VLLM_URL=http://10.100.0.121:8932/v1/chat/completions
ENV VLLM_MODEL=openai/gpt-oss-120b

CMD ["python", "main.py"]
