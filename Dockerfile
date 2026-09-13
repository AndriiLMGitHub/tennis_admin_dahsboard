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
    PYTHONPATH=/app/src

# Встановлюємо робочу директорію одразу в корінь Django-проєкту
WORKDIR /app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо залежності
COPY requirements.txt /app/
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip \
    && pip install --no-index --find-links=/wheels -r /app/requirements.txt \
    && rm -rf /wheels

RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && mkdir -p /var/run/celery \
    && chown -R django:django /var/run/celery

# Створюємо непривілейованого користувача
RUN addgroup --system django \
    && adduser --system --ingroup django django

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Копіюємо код і передаємо права
COPY --chown=django:django . /app/

# ЗБІРКА СТАТИКИ ПІД ЧАС BUILD
# Dummy-змінні потрібні, щоб обійти валідацію settings.py без доступу до реальної БД
RUN SECRET_KEY=dummy-key-for-build \
    DATABASE_URL=sqlite:////tmp/dummy.db \
    CELERY_BROKER_URL=redis://dummy \
    python manage.py collectstatic --noinput --clear

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]