---
description: How to deploy Second Brain changes to VPS
---

### 1. Сохранение изменений локально
Открой терминал в папке проекта и выполни команды для отправки кода на GitHub:

```bash
git add .
git commit -m "Add Second Brain 2026 architecture: Bouncer, Fix Button, and enhanced AI"
git push origin main
```

### 2. Обновление на VPS
Зайди на свой сервер по SSH и обнови проект:

```bash
# Подключение к серверу
ssh root@156.67.63.13

# Переход в папку проекта (замени на свой путь, если он другой)
cd /root/Second-Brain 

# Получение обновлений
git pull origin main

# Пересборка и перезапуск Docker
docker compose up -d --build
```

### 3. Проверка логов
Убедись, что бот запустился без ошибок:

```bash
docker compose logs -f
```
