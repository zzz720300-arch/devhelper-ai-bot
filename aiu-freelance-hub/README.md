# AIU-FREELANCE-HUB

AIU-FREELANCE-HUB — автономная фабрика фриланс-профилей. Проект объединяет несколько псевдо-профилей исполнителей, единый телеграм-центр управления и ядро автоматического выполнения задач.

## 📦 Быстрый старт

```bash
git clone <repo>
cd aiu-freelance-hub
cp .env.example .env
make init  # по желанию
```

### Docker

```bash
docker-compose up --build
```

Сервисы:
- `bot`: телеграм-бот-оператор.
- `core`: FastAPI ядро.
- `db`: PostgreSQL 15.
- `redis`: кеш, трекинг ограничений.

После запуска:
- FastAPI доступен на `http://localhost:8000/docs`.
- Телеграм-бот работает после указания `BOT_TOKEN`.

## 🏗 Архитектура

```
aiu-freelance-hub/
 ├─ bot/
 │   ├─ main.py            # запуск aiogram 3, регистрация хендлеров
 │   ├─ lead_collector.py  # сбор заказов, запись в БД
 │   ├─ handlers/
 │   │   ├─ start.py
 │   │   ├─ leads.py
 │   │   ├─ approve.py
 │   │   └─ stats.py
 │   ├─ adapters/          # API площадок
 │   │   ├─ freelanceru.py
 │   │   ├─ kwork.py
 │   │   ├─ habr.py
 │   │   └─ telegram.py
 │   └─ utils/
 │       ├─ config.py
 │       ├─ db.py
 │       └─ keyboards.py
 ├─ core/
 │   ├─ main.py
 │   ├─ middleware.py      # ограничение нагрузки
 │   ├─ routes/
 │   │   ├─ process.py
 │   │   ├─ payments.py
 │   │   └─ stats.py
 │   └─ handlers/
 │       ├─ docker_handler.py
 │       ├─ deploy_handler.py
 │       └─ report_handler.py
 ├─ db/
 │   ├─ models.py
 │   └─ session.py
 ├─ docker-compose.yml
 ├─ requirements.txt
 ├─ .env.example
 └─ README.md
```

## 🛠 Основные возможности

- Имитация нескольких профилей-фрилансеров и маршрутизация заказов.
- Автоматический сбор лидов через адаптеры площадок.
- Подтверждение откликов и платежей владельцем.
- Оплата через ЮKassa перед запуском ядра.
- Исполнение задач ядром (Docker, Deploy, Report).
- Ограничение запросов к ядру: 4/мин и 3000/сутки.
- Хранение жалоб, статистики, отчётов.

## ⚙️ Настройки

Создайте файл `.env`:

```env
BOT_TOKEN=...
CORE_URL=http://core:8000
POSTGRES_DSN=postgresql://aiu:pass@db:5432/aiu_freelance
REDIS_URL=redis://redis:6379/0
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
ADMIN_IDS=123456789
```

## 🧪 Тестовые запросы

```bash
curl -X POST http://localhost:8000/process/run \
  -H "Content-Type: application/json" \
  -d '{"order_id": "test-order", "task_type": "docker"}'
```

## 🗄 Миграции

Для создания таблиц используется SQLAlchemy с декларативными моделями. При первом запуске `core` автоматически создаёт таблицы.

## 📝 Лицензия

MIT.
