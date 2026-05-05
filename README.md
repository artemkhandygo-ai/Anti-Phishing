# Anti-Phishing
Anti-Phishing — это проектная часть моей диплоиной работы на тему противодействия фишинговым атакам на основе мессенджер-бота. Система получает входящие письма по IMAP, анализирует их с помощью гибридного подхода (эвристические правила + ML-модель), создаёт инциденты с объяснениями причин риска и отправляет уведомления пользователю в Telegram.

# Назначение проекта
Проект предназначен для автоматизированного анализа электронных писем и оперативного уведомления пользователя о потенциально опасных сообщениях. Система классифицирует письмо по уровню риска:
- `safe` — безопасное письмо
- `suspicious` — подозрительное письмо, требующее внимания
- `phishing` — письмо с выраженными признаками фишинговой атаки
Для каждого инцидента сохраняются итоговый риск-балл, балл правил, балл ML-модели, причины срабатывания и обратная связь пользователя из Telegram.

# Основные возможности
- получение писем из почтового ящика через IMAP;
- разбор темы, отправителя, Reply-To, текста, HTML, ссылок, вложений и заголовков;
- проверка ссылок: короткие ссылки, HTTP, IP-адреса, редиректы, login-страницы;
- глубокий анализ веб-страниц по ссылкам: формы входа, сбор паролей, сбор платёжных данных, внешний `form action`, имитация бренда;
- проверка почтовой инфраструктуры: SPF, DMARC, MX, From/Reply-To, punycode/lookalike-домены, Received IP;
- анализ текста письма: срочность, запрос пароля/кода, финансовая просьба, приз/мошенническая акция, телефонный номер;
- анализ вложений по опасным расширениям;
- гибридная оценка риска: правила + ML-модель;
- сохранение писем и инцидентов в PostgreSQL;
- фоновые задачи через Celery + Redis;
- Telegram-уведомления с кнопками feedback;
- экспорт инцидентов в JSON и CSV;
- запуск обучения ML-модели через API.

# Стек технологий
- Python 3.11;
- FastAPI;
- PostgreSQL;
- Redis;
- Celery / Celery Beat;
- SQLAlchemy / Alembic;
- scikit-learn / joblib;
- Docker / Docker Compose;
- Telegram Bot API;
- IMAP / SMTP для тестовой отправки писем.

```text
# Структура проекта
Anti-Phishing/
├── app/
│   ├── api/                 # API-эндпоинты FastAPI
│   ├── bot/                 # Telegram-сообщения, клавиатуры и API
│   ├── core/                # настройки и базовая конфигурация
│   ├── db/                  # модели БД, репозитории, миграции Alembic
│   ├── features/            # извлечение признаков из письма
│   ├── mail/                # IMAP-клиент и сервис получения писем
│   ├── ml/                  # обучение, загрузка и применение ML-модели
│   ├── network_checks/      # DNS/SPF/DMARC/MX и deep-link проверки
│   ├── parser/              # парсинг email, HTML, ссылок и вложений
│   ├── rules/               # эвристические правила анализа
│   ├── schemas/             # Pydantic-схемы
│   ├── services/            # основная бизнес-логика анализа
│   ├── tasks/               # Celery-задачи
│   └── utils/               # вспомогательные функции
├── data/
│   ├── config/              # конфигурационные списки, whitelist
│   ├── datasets/            # обучающие датасеты
│   └─── models/              # обученная ML-модель и метрики
├── docker/                  # Dockerfile для app/worker/trainer
├── scripts/                 # служебные скрипты
├── docker-compose.yml
├── requirements.txt
├── .env
├── README.md
└── TESTING.md
```
# Подготовка окружения
Перед запуском нужен Docker Desktop.
Заполнить `.env` значениями:
```text
MAIL_IMAP_USERNAME=............
MAIL_IMAP_PASSWORD=............
MAIL_IMAP_FOLDER=INBOX
TELEGRAM_BOT_TOKEN=............
TELEGRAM_CHAT_ID=..............
```
# Запуск проекта
В корне проекта:
```text
powershell:
docker compose down
docker compose build --no-cache
docker compose up
``` 
После запуска Swagger доступен по адресу:
http://localhost:8000/docs

Проверка состояния API:
GET /health

Ожидаемый ответ:
json:
{"status": "ok"}

# Основные API-эндпоинты
- `GET /health` — проверка работоспособности API;
- `POST /emails/fetch?limit=10` — вручную поставить задачу получения писем;
- `GET /incidents` — список инцидентов;
- `GET /incidents/export.json` — экспорт инцидентов в JSON;
- `GET /incidents/export.csv` — экспорт инцидентов в CSV;
- `GET /ml/model/info` — информация об обученной модели;
- `POST /ml/train` — запуск обучения модели;
- `GET /ml/train/status/{task_id}` — статус обучения модели.

# Анализ письма
1. `beat` раз в заданный интервал ставит задачу проверки почты.
2. `worker` подключается к IMAP и забирает новые письма.
3. Парсер извлекает тело письма, ссылки, вложения, заголовки и отправителя.
4. Feature pipeline собирает признаки текста, ссылок, вложений и заголовков.
5. Rules engine формирует объяснимые причины срабатывания.
6. ML-модель выдаёт свой балл риска.
7. Гибридная логика рассчитывает итоговый `risk_score` и `risk_level`.
8. Инцидент сохраняется в PostgreSQL.
9. Telegram-бот отправляет уведомление пользователю.
10. Пользователь может нажать feedback-кнопку: «Это безопасно», «Это фишинг», «Ложное срабатывание».

# Примеры ключевых причин срабатывания
- `URL_LOGIN_KEYWORDS` — в ссылке есть слова login/verify/account/password;
- `LOGIN_PAGE_LINK` — по ссылке открывается страница входа;
- `CREDENTIAL_COLLECTION_PAGE` — страница собирает логин/пароль;
- `PAYMENT_COLLECTION_PAGE` — страница собирает платёжные данные;
- `BRAND_MISMATCH_PAGE` — страница имитирует бренд на неподходящем домене;
- `SHORTENED_LINK` — короткая ссылка;
- `IP_URL` — ссылка на IP-адрес;
- `NON_HTTPS_LINK` — ссылка без HTTPS;
- `FROM_REPLY_MISMATCH` — From и Reply-To указывают на разные домены;
- `LOOKALIKE_REPLY_DOMAIN` — Reply-To похож на домен отправителя;
- `PUNYCODE_DOMAIN` — punycode-домен;
- `AUTH_FAIL` — SPF/DKIM/DMARC не пройдены;
- `NO_SPF_POLICY`, `NO_DMARC_POLICY`, `NO_MX_RECORD` — отсутствуют SPF/DMARC/MX;
- `DANGEROUS_ATTACHMENT` — опасное расширение вложения;
- `PASSWORD_REQUEST` — письмо просит пароль или код;
- `FINANCIAL_REQUEST` — финансовая просьба;
- `PROMO_SCAM`, `PHONE_NUMBER_SCAM` — призовая/телефонная мошенническая схема;
- `WHITELISTED_SENDER` — отправитель находится в белом списке.

# Белый список отправителей
Файл белого списка:
data/config/whitelist_emails.txt

Можно указывать адреса или домены:
trusted@example.com
@trusted-domain.com

Если отправитель найден в whitelist, система выставляет:
`risk_level = safe`
`model_version = whitelist_override`
`reason = WHITELISTED_SENDER`

# Данные и модель
- `data/datasets/` — датасеты для обучения;
- `data/models/phishguard_model.joblib` — обученная модель;
- `data/models/train_metrics.json` — метрики обучения;
- `data/processed/` — место для обработанных данных.

# Примечание по DNS-тестам
Проверки SPF, DMARC и MX зависят от внешних DNS-резолверов. Если DNS-записи только что изменялись, результат может обновиться не мгновенно.

# Быстрая проверка
1. Открыть `http://localhost:8000/docs`.
2. Выполнить `GET /health`.
3. Выполнить `GET /ml/model/info`.
4. Отправить тестовое письмо.
5. Проверить `GET /incidents`.

# Тестирование
Подробный порядок тестирования находится в файле `TESTING.md`.
