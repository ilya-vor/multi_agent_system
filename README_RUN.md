# Быстрый запуск multi_agent_system

Краткая инструкция для локального запуска агента. Рекомендуется использовать Python 3.10 или 3.11 — некоторые зависимости (например, `slixmpp_multiplatform`) могут быть недоступны для более новых версий.

1) Создать виртуальное окружение (PowerShell):

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Если установка выдаёт ошибку с `slixmpp_multiplatform` — смените версию Python на 3.10/3.11 и повторите.

2) Пример запуска агента (из корня проекта):

```powershell
.\.venv\Scripts\python.exe .\common\main.py --jid worker1@xmpp.example --password secret \
  --backpack-file .\backpacks\old\backpack1.json --other_workers worker2@xmpp.example \
  --specialization сварщик
```

Пояснения:
- `--jid` и `--password` — учётные данные XMPP-аккаунта. Для реального запуска нужен работающий XMPP-сервер и зарегистрированные аккаунты.
- `--backpack-file` — путь к JSON-файлу с рюкзаком/задачами (в репозитории есть `backpacks/old/backpack1.json`).
- `--other_workers` — JID(ы) других агентов, с которыми агент может связываться.
- `--specialization` — одна из: `сварщик`, `слесарь`, `токарь`.

3) Быстрый тест без XMPP (ограниченный):

Если вы хотите только проверить, что скрипты запускаются (синтаксис, чтение рюкзака и т.п.) без соединения с XMPP, можно временно запустить простой «smoke» модуль, но полноценная работа агентов требует XMPP-сервера.

4) Если нужна помощь — могу:
- попытаться локально (в вашем окружении) выполнить создание venv и `pip install -r requirements.txt` и прислать лог ошибок;
- подобрать совместимые версии зависимостей, если установка падает (например, зафиксировать другую версию `spade` или заменить проблемный пакет).

