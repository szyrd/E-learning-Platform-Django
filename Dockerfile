# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl is used by the compose healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY elearning/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY elearning/ /app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "elearning.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
