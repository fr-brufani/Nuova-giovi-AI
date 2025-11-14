# Stage 1: Build dependencies (if needed)
FROM python:3.12-slim AS builder

WORKDIR /usr/src/app

# Installa build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia pyproject.toml e installa dipendenze
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build wheel && \
    pip install --no-cache-dir -e .

# Stage 2: Production image
FROM python:3.12-slim AS production

WORKDIR /usr/src/app

# Installa solo runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia pyproject.toml
COPY pyproject.toml ./

# Installa solo dipendenze di produzione
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copia tutto il codice sorgente
COPY . .

# Esponi la porta (Cloud Run usa $PORT, default 8080)
EXPOSE 8080

# Variabile d'ambiente per la porta (Cloud Run la imposta automaticamente)
ENV PORT=8080

# Health check (usa 8080 come fallback se PORT non è settato)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Avvia l'applicazione (uvicorn leggerà PORT da env)
CMD sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1'

