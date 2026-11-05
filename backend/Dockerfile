# Build context = repository root (so ai_engine/ is included):  docker build -f backend/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY ai_engine ai_engine
RUN useradd -m app && mkdir -p /srv/backend/uploads && chown -R app /srv/backend/uploads
USER app
WORKDIR /srv/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
