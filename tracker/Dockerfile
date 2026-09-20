# Imagem otimizada para o Tracker de Visão Computacional com uv e OpenCV
FROM python:3.12-slim

# Evita buffer no stdout para logs em tempo real com `docker logs`
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=true

# Instala bibliotecas de sistema necessárias para o OpenCV rodar no Debian/Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instala o binário oficial do uv diretamente da imagem de release
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Diretório de trabalho no container
WORKDIR /app

# Copia arquivos de dependências primeiro para aproveitar o cache de camadas do Docker
COPY pyproject.toml README.md ./

# Instala dependências usando uv
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copia o código-fonte e arquivos de configuração padrão
COPY src/ ./src/
COPY tokens_config.json ./tokens_config.json

# Executa o pacote em modo headless por padrão no container
CMD ["uv", "run", "python", "-m", "tracker.main", "--headless"]
