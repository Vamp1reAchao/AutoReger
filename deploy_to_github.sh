#!/bin/bash

echo "========================================"
echo "   GitHub Deploy Script for RegerAiogram"
echo "========================================"
echo

# Проверяем наличие git
if ! command -v git &> /dev/null; then
    echo "[ERROR] Git не установлен! Установите Git и повторите попытку."
    exit 1
fi

# Переходим в папку проекта
cd "$(dirname "$0")"

# Инициализируем git репозиторий если его нет
if [ ! -d ".git" ]; then
    echo "[INFO] Инициализация Git репозитория..."
    git init
fi

# Создаем .gitignore если его нет
if [ ! -f ".gitignore" ]; then
    echo "[INFO] Создание .gitignore..."
    cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*\$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Logs
logs/
*.log

# Sessions
sessions/
*.session

# Config
config_local.py
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Data
data/proxies.txt
EOF
fi

# Добавляем все файлы
echo "[INFO] Добавление файлов в Git..."
git add .

# Делаем коммит
echo "[INFO] Создание коммита..."
git commit -m "Initial commit: RegerAiogram - Telegram Account Registration Bot"

# Запрашиваем URL репозитория
echo
echo "[INPUT] Введите URL вашего GitHub репозитория:"
echo "Пример: https://github.com/username/RegerAiogram.git"
read -p "URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "[ERROR] URL репозитория не указан!"
    exit 1
fi

# Добавляем remote origin
echo "[INFO] Добавление remote origin..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

# Пушим в репозиторий
echo "[INFO] Загрузка в GitHub..."
git branch -M main
if git push -u origin main; then
    echo
    echo "========================================"
    echo "[SUCCESS] Проект успешно загружен на GitHub!"
    echo "URL: $REPO_URL"
    echo "========================================"
else
    echo
    echo "[ERROR] Ошибка при загрузке в GitHub!"
    echo "Возможные причины:"
    echo "- Неверный URL репозитория"
    echo "- Нет прав доступа к репозиторию"
    echo "- Проблемы с аутентификацией"
    echo
    echo "Попробуйте:"
    echo "1. Проверить URL репозитория"
    echo "2. Настроить Git credentials: git config --global user.name \"Your Name\""
    echo "3. Настроить Git email: git config --global user.email \"your.email@example.com\""
    exit 1
fi