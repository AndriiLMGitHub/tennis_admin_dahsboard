# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    PYTHONPATH=/app/src

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip \
    && pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && addgroup --system django \
    && adduser --system --ingroup django django

COPY --chown=django:django . .
RUN mkdir -p /app/src/staticfiles \
    && chown -R django:django /app/src/staticfiles

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
