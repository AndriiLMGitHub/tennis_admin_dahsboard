# Tennis Admin Dashboard

Адміністративна платформа для керування консультаційними заявками у тенісному сервісі. Проєкт побудований на Django і покриває роботу студентів, тренерів, нутриціологів, психологів та адміністратора.

## Основні можливості

- реєстрація та авторизація користувачів через email;
- рольова модель користувачів: `Student`, `Coach`, `Nutrition`, `Psychology`;
- модерація статусу користувачів: `pending`, `approved`, `rejected`;
- створення студентами заявок на консультації;
- домени консультацій: теніс, нутриціологія, психологія;
- робота з медіа: відео, файли, YouTube-посилання;
- завантаження файлів у Cloudflare R2;
- формування звітів тренера і завантаження DOCX;
- окремі dashboard-розділи для студентів, тренерів, нутриціологів, психологів і superadmin;
- feedback-форма та FAQ;
- фонові задачі через Celery і Redis;
- production-ready Docker setup з PostgreSQL, Redis, Gunicorn і WhiteNoise.

## Технології

- Python 3.13
- Django 6
- PostgreSQL
- Redis
- Celery
- Gunicorn
- WhiteNoise
- django-allauth
- django-storages / boto3
- Cloudflare R2
- Docker / Docker Compose

## Структура проєкту

```text
.
├── Dockerfile
├── docker-compose.yml
├── docker/
│   └── entrypoint.sh
├── requirements.txt
├── .env.example
└── src/
    ├── manage.py
    ├── config/
    │   ├── settings.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   ├── asgi.py
    │   └── celery.py
    ├── apps/
    │   ├── accounts_core/
    │   ├── consulting/
    │   └── feedback/
    ├── infrastructure/
    │   ├── email/
    │   ├── r2_storage/
    │   └── telegram/
    ├── templates/
    ├── static/
    └── locale/
```

## Швидкий запуск через Docker

Перед запуском переконайся, що Docker Desktop або Docker daemon запущений.

1. Створи `.env` на основі прикладу:

```bash
cp .env.example .env
```

2. Заповни змінні у `.env`.

Мінімально потрібні для локального Docker-запуску:

```env
DEBUG=False
SECRET_KEY=change-me-to-a-long-random-secret

ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
WEB_PORT=8000

POSTGRES_DB=tennis_admin
POSTGRES_USER=tennis
POSTGRES_PASSWORD=change-me
```

Для роботи email і Cloudflare R2 також потрібні:

```env
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_CUSTOM_DOMAIN=
```

3. Запусти інфраструктуру:

```bash
docker compose up --build
```

Після старту застосунок буде доступний за адресою:

```text
http://localhost:8000
```

## Docker-сервіси

`docker-compose.yml` піднімає такі сервіси:

- `web` - Django application через Gunicorn;
- `worker` - Celery worker для фонових задач;
- `beat` - Celery beat для scheduled tasks;
- `db` - PostgreSQL;
- `redis` - брокер і result backend для Celery.

Під час старту `web` автоматично виконує:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
```

## Корисні Docker-команди

Запустити проєкт:

```bash
docker compose up --build
```

Запустити у фоні:

```bash
docker compose up -d --build
```

Подивитися логи:

```bash
docker compose logs -f
```

Логи тільки web-сервісу:

```bash
docker compose logs -f web
```

Зупинити контейнери:

```bash
docker compose down
```

Зупинити контейнери та видалити volumes з базою і Redis:

```bash
docker compose down -v
```

Виконати Django-команду:

```bash
docker compose exec web python manage.py check
```

Створити superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

Запустити shell:

```bash
docker compose exec web python manage.py shell
```

## Локальний запуск без Docker

Docker є рекомендованим способом запуску, але проєкт можна запустити і напряму.

1. Створи та активуй virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

2. Встанови залежності:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Створи `.env`:

```bash
cp .env.example .env
```

4. Для локального запуску можна використати PostgreSQL через `DATABASE_URL` або SQLite fallback. Для повноцінної роботи Celery потрібен Redis.

Приклад локальних змінних:

```env
DEBUG=True
SECRET_KEY=local-dev-secret-key
DATABASE_URL=postgres://tennis:tennis@localhost:5432/tennis_admin
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

5. Виконай міграції:

```bash
cd src
python manage.py migrate
```

6. Збери static files:

```bash
python manage.py collectstatic --noinput
```

7. Запусти dev server:

```bash
python manage.py runserver
```

## Celery

Для запуску Celery локально Redis має бути доступний за адресою з `CELERY_BROKER_URL`.

Worker:

```bash
cd src
celery -A config worker --loglevel=info
```

Beat:

```bash
cd src
celery -A config beat --loglevel=info
```

У Docker ці процеси вже винесені в окремі сервіси `worker` і `beat`.

## Основні маршрути

Проєкт використовує локалізовані URL через `i18n_patterns`, тому маршрути доступні з мовним префіксом, наприклад `/en/`.

Основні розділи:

```text
/en/admin/
/en/accounts/
/en/dashboard/
/en/dashboard/consulting/student/requests/
/en/dashboard/consulting/student/requests/create/
/en/dashboard/consulting/coach/requests/
/en/dashboard/consulting/nutrition/nutrition/
/en/dashboard/consulting/nutrition/nutrition/schedule/
/en/dashboard/consulting/psychology/
/en/dashboard/consulting/psychology/schedule/
/en/dashboard/consulting/superadmin/
/en/dashboard/feedback/contact_us/
/en/dashboard/feedback/faq/
```

## Змінні середовища

| Змінна | Призначення |
| --- | --- |
| `DEBUG` | Режим Django debug. Для production має бути `False`. |
| `SECRET_KEY` | Секретний ключ Django. Має бути довгим і унікальним. |
| `ALLOWED_HOSTS` | Дозволені hostnames, через кому. |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins для CSRF, через кому. |
| `WEB_PORT` | Локальний порт для Docker web-сервісу. |
| `POSTGRES_DB` | Назва PostgreSQL бази у Docker. |
| `POSTGRES_USER` | PostgreSQL користувач у Docker. |
| `POSTGRES_PASSWORD` | PostgreSQL пароль у Docker. |
| `DATABASE_URL` | URL бази даних для Django. У Docker формується автоматично з `POSTGRES_*`. |
| `CELERY_BROKER_URL` | Redis URL для Celery broker. |
| `CELERY_RESULT_BACKEND` | Redis URL для Celery result backend. |
| `EMAIL_HOST_USER` | SMTP email користувач. |
| `EMAIL_HOST_PASSWORD` | SMTP пароль або app password. |
| `R2_ACCOUNT_ID` | Cloudflare R2 account id. |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key. |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key. |
| `R2_BUCKET_NAME` | Назва R2 bucket. |
| `R2_CUSTOM_DOMAIN` | Public domain для R2 media files. |

## Static і media files

Static files зберігаються у `src/static` і збираються у `src/staticfiles`.

У Docker static files роздаються через WhiteNoise після `collectstatic`.

Media files користувачів зберігаються у Cloudflare R2 через `django-storages`. Для цього потрібно коректно заповнити всі `R2_*` змінні у `.env`.

## Міграції

Створити міграції:

```bash
python src/manage.py makemigrations
```

Застосувати міграції локально:

```bash
python src/manage.py migrate
```

Застосувати міграції в Docker:

```bash
docker compose exec web python manage.py migrate
```

## Перевірка проєкту

Django system check:

```bash
python src/manage.py check
```

У Docker:

```bash
docker compose exec web python manage.py check
```

Production checklist warnings:

```bash
python src/manage.py check --deploy
```

Для production очікується, що `DEBUG=False`, `SECRET_KEY` не є dev-ключем, cookies працюють через HTTPS, а домени задані явно.

## Production нотатки

Перед production-деплоєм потрібно:

- встановити `DEBUG=False`;
- задати сильний `SECRET_KEY`;
- замінити дефолтний `POSTGRES_PASSWORD`;
- вказати реальні `ALLOWED_HOSTS`;
- вказати реальні `CSRF_TRUSTED_ORIGINS` з `https://`;
- налаштувати HTTPS на reverse proxy або load balancer;
- перевірити Cloudflare R2 credentials;
- перевірити SMTP credentials;
- налаштувати backup PostgreSQL;
- не комітити `.env` у репозиторій.

## Troubleshooting

Якщо Docker пише, що не може підключитися до `docker.sock`, запусти Docker Desktop і повтори команду:

```bash
docker compose up --build
```

Якщо web-контейнер не стартує, спочатку перевір логи:

```bash
docker compose logs -f web
```

Якщо Celery не обробляє задачі, перевір Redis і worker:

```bash
docker compose logs -f redis
docker compose logs -f worker
```

Якщо static files не відображаються, перезапусти збір static files:

```bash
docker compose exec web python manage.py collectstatic --noinput --clear
```

Якщо потрібно повністю почати з чистої Docker-бази:

```bash
docker compose down -v
docker compose up --build
```
