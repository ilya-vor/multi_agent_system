import sys
import os

async def start():
    # Параметры для подключения
    params = [
        "--jid", "hiker3@26.3.185.180",
        "--password", "hiker3",
        "--backpack-file", "backpack3.json",
        "--other_hikers", "hiker1@26.3.185.180+hiker2@26.3.185.180",
        "--server", "26.3.185.180"
    ]

    # Подменяем sys.argv для передачи параметров
    sys.argv = [sys.argv[0]] + params

    # Импортируем и запускаем основной модуль
    from main import main
    import asyncio

    # Для отладчика - устанавливаем точку останова здесь
    print("Запуск агента hiker3...")
    await main()

# Добавляем возможность запуска с параметрами командной строки
if __name__ == "__main__":
    start()