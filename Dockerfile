FROM python:3.12-slim AS builder


RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


COPY . .


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --from=builder /app /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN chmod +x start.sh

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1


CMD ["./start.sh"]
