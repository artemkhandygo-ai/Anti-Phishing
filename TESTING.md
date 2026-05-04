# Anti-Phishing — инструкция по частичному тестированию

## 0. Подготовка

1. Заполнить .env своими данными:

MAIL_IMAP_USERNAME=your_mailru_login;
MAIL_IMAP_PASSWORD=your_mailru_app_password;

TELEGRAM_BOT_TOKEN=your_telegram_bot_token;
TELEGRAM_CHAT_ID=your_telegram_chat_id;

2. Запустить проект:

powershell:
docker compose down
docker compose build --no-cache
docker compose up

3. Проверить контейнеры:

powershell:
docker compose ps

Ожидаемые сервисы:
app
worker
beat
trainer
db
redis

## 1. Базовые API-проверки

### Тест 1 — health-check

Endpoint:
GET /health

Ожидаемый ответ:
json:
{"status": "ok"}

### Тест 2 — информация о ML-модели

Endpoint:
GET /ml/model/info

Ожидаемо:
model_exists = true
model_type = hybrid_ensemble_v4
metrics_exists = true

### Тест 3 — список инцидентов

Endpoint:
GET /incidents

На чистой базе может быть пустой список. Если тесты уже проводились, будет список инцидентов.

## 2. Проверка исправлений URL и MILD_URGENCY

### Тест 4 — login-страница без ложной срочности
Отправить письмо:
"Пожалуйста, откройте страницу:
https://login-test-6jq.pages.dev/
Спасибо."

Ожидаемые причины:
URL_LOGIN_KEYWORDS
LOGIN_PAGE_LINK
CREDENTIAL_COLLECTION_PAGE

### Тест 5 — URL в скобках
Отправить письмо:
"Пожалуйста, откройте страницу (https://login-test-6jq.pages.dev/)"

Ожидаемо: ссылка корректно очистится от `)` и сработают:
URL_LOGIN_KEYWORDS
LOGIN_PAGE_LINK
CREDENTIAL_COLLECTION_PAGE

## 4. Основные правила анализа ссылок

### Тест 6 — обычное безопасное письмо
Отправить письмо:
"Это обычное тестовое письмо без ссылок и вложений."

Ожидаемо:
risk_level = safe
reason = BENIGN_PATTERN

### Тест 7 — короткая ссылка
Отправить письмо:
"Проверь ссылку: https://bit.ly/test-check-link"

Ожидаемо:
SHORTENED_LINK

### Тест 8 — IP URL и HTTP
Отправить письмо:
"Материалы доступны по ссылке: http://198.51.100.42/share/meeting-notes"

Ожидаемо:
IP_URL
NON_HTTPS_LINK

### Тест 9 — redirect
Отправить письмо:
"Добрый день, вот ссылка для нашей встречи :
https://httpbin.org/redirect-to?url=https%3A%2F%2Fexample.com%2Ffile "

Ожидаемо:
REDIRECTED_DOMAIN

### Тест 10 — опасная deep-link страница
Отправить письмо:
"Откройте страницу:
https://danger.phish-lab-test.uk
Спасибо"

Ожидаемо:
LOGIN_PAGE_LINK
EXTERNAL_FORM_ACTION
BRAND_MISMATCH_PAGE
CREDENTIAL_COLLECTION_PAGE
PAYMENT_COLLECTION_PAGE
risk_level = phishing

## 5. Проверка отправителя и DNS

## Код для отправки сообщений:
import smtplib
from email.message import EmailMessage
SMTP_HOST = "smtp.mail.ru"
SMTP_PORT = 465
FROM_EMAIL = "............." 
PASSWORD = "..............."
TO_EMAIL = "..............."
REPLY_TO_EMAIL = "........."

msg = EmailMessage()
msg["Subject"] = "plhfdcndeqnt"
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL
msg["Reply-To"] = REPLY_TO_EMAIL
msg.set_content(
    """Здравствуйте.
Направляю уточнение по документу.
Посмотрите, пожалуйста, когда будет удобно.
"""
)
with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
    smtp.login(FROM_EMAIL, PASSWORD)
    smtp.send_message(msg)

print("Письмо отправлено")

### Тест 11 — From/Reply-To mismatch

REPLY_TO_EMAIL = "support@other-domain.test"

Ожидаемо:
FROM_REPLY_MISMATCH

### Тест 12 — lookalike Reply-To

Для этого теста From должен быть похож на Reply-To:
REPLY_TO_EMAIL = "support@rnail.ru"

Ожидаемо:
FROM_REPLY_MISMATCH
LOOKALIKE_REPLY_DOMAIN

### Тест 13 — punycode Reply-To

REPLY_TO_EMAIL = "support@xn--pple-43d.com"

Ожидаемо:
FROM_REPLY_MISMATCH
PUNYCODE_DOMAIN

## 6. Текстовые правила

### Тест 14 — запрос пароля/кода

Отправить письмо:
"Пожалуйста, отправьте ваш пароль и код подтверждения для восстановления доступа."

Ожидаемо:
PASSWORD_REQUEST

### Тест 15 — сильная срочность

Отправить письмо:
"Срочно подтвердите вход прямо сейчас."

Ожидаемо:
URGENT_LANGUAGE

### Тест 16 — слабая срочность

Отправить письмо:
"Пожалуйста, подтвердите получение письма."

Ожидаемо:
MILD_URGENCY

### Тест 17 — финансовая просьба

Отправить письмо:
"Срочно оплати счёт и сделай перевод по реквизитам сегодня."

Ожидаемо:
FINANCIAL_REQUEST
URGENT_LANGUAGE или MILD_URGENCY

### Тест 18 — приз и телефон

Отправить письмо:
"Вы выиграли приз. Срочно позвоните по номеру +7 999 123 45 67, чтобы забрать выигрыш."

Ожидаемо:
PROMO_SCAM
PHONE_NUMBER_SCAM

## 7. Обучение модели

### Тест 19 — запуск обучения

Endpoint:
POST /ml/train

Ожидаемо:
status = queued
task_id присутствует

### Тест 20 — статус обучения

Endpoint:
GET /ml/train/status/{task_id}

После завершения ожидаемо:
state = SUCCESS
status = completed

## 8. Устойчивость и экспорт

### Тест 21 — полный перезапуск

powershell:
docker compose down
docker compose up --build

Проверить:
GET /health
GET /incidents
GET /ml/model/info

Ожидаемо: API работает, инциденты и модель сохранились.

### Тест 22 — экспорт JSON

Endpoint:
GET /incidents/export.json

Ожидаемо: JSON выгружается и содержит инциденты с `reasons`.

### Тест 23 — экспорт CSV

Endpoint:
GET /incidents/export.csv

Ожидаемо: CSV выгружается и содержит колонки:
incident_id,email_id,created_at,risk_level,risk_score,rule_score,ml_score,status,from_email,subject,reason_codes,feedback