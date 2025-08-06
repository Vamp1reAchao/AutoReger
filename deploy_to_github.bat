@echo off
echo ========================================
echo    GitHub Deploy Script for RegerAiogram
echo ========================================
echo.

REM Проверяем наличие git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не установлен! Установите Git и повторите попытку.
    pause
    exit /b 1
)

REM Переходим в папку проекта
cd /d "%~dp0"

REM Инициализируем git репозиторий если его нет
if not exist ".git" (
    echo [INFO] Инициализация Git репозитория...
    git init
)

REM Создаем .gitignore если его нет
if not exist ".gitignore" (
    echo [INFO] Создание .gitignore...
    (
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo *$py.class
        echo *.so
        echo .Python
        echo env/
        echo venv/
        echo ENV/
        echo env.bak/
        echo venv.bak/
        echo.
        echo # Logs
        echo logs/
        echo *.log
        echo.
        echo # Sessions
        echo sessions/
        echo *.session
        echo.
        echo # Config
        echo config_local.py
        echo .env
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo.
        echo # OS
        echo .DS_Store
        echo Thumbs.db
        echo.
        echo # Data
        echo data/proxies.txt
    ) > .gitignore
)

REM Добавляем все файлы
echo [INFO] Добавление файлов в Git...
git add .

REM Делаем коммит
echo [INFO] Создание коммита...
git commit -m "Initial commit: RegerAiogram - Telegram Account Registration Bot"

REM Запрашиваем URL репозитория
echo.
echo [INPUT] Введите URL вашего GitHub репозитория:
echo Пример: https://github.com/username/RegerAiogram.git
set /p REPO_URL=URL: 

if "%REPO_URL%"=="" (
    echo [ERROR] URL репозитория не указан!
    pause
    exit /b 1
)

REM Добавляем remote origin
echo [INFO] Добавление remote origin...
git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%

REM Пушим в репозиторий
echo [INFO] Загрузка в GitHub...
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка при загрузке в GitHub!
    echo Возможные причины:
    echo - Неверный URL репозитория
    echo - Нет прав доступа к репозиторию
    echo - Проблемы с аутентификацией
    echo.
    echo Попробуйте:
    echo 1. Проверить URL репозитория
    echo 2. Настроить Git credentials: git config --global user.name "Your Name"
    echo 3. Настроить Git email: git config --global user.email "your.email@example.com"
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Проект успешно загружен на GitHub!
echo URL: %REPO_URL%
echo ========================================
echo.
pause