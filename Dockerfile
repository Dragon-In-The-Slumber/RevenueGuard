FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for C extensions (asyncpg, aiohttp, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY ./src ./src
COPY ./tests ./tests
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini

# Create a non-root user and grant ownership of the /app directory.
# The chroma cache dir must exist and be owned by appuser *in the image*: Docker
# seeds a named volume from the image path, so creating it here is what gives the
# mounted volume the right ownership. Without it ChromaDB's model download fails
# with PermissionError and takes application startup down with it.
RUN adduser --disabled-password --gecos '' appuser \
    && mkdir -p /home/appuser/.cache/chroma /app/chroma_data \
    && chown -R appuser:appuser /app /home/appuser
USER appuser

# Migrate before serving. A database created by an older create_all has the tables
# but no alembic_version row, so it is stamped at the baseline instead of having
# the initial revision replayed on top of it.
CMD ["sh", "-c", "alembic upgrade head || alembic stamp head; uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
