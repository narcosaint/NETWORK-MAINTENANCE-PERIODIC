FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && groupadd --system app && useradd --system --gid app app
COPY --chown=app:app backend/app /app/backend/app
COPY --chown=app:app database /app/database
COPY --chown=app:app alembic.ini /app/alembic.ini
RUN mkdir -p /app/storage/photos && chown -R app:app /app/storage
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
