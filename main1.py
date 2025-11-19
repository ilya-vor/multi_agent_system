import sys


async def start():
    # Параметры для подключения
    params = [
        "--jid", "hiker1@26.3.185.180",
        "--password", "hiker1",
        "--backpack-file", "backpacks/old/backpack1.json",
        "--other_hikers", "hiker2@26.3.185.180+hiker3@26.3.185.180+hiker4@26.3.185.180",
        "--server", "26.3.185.180"
    ]

    # Подменяем sys.argv для передачи параметров
    sys.argv = [sys.argv[0]] + params

    # Импортируем и запускаем основной модуль
    import main

    # Для отладчика - устанавливаем точку останова здесь
    print("Запуск агента hiker1...")
    await main.main()

# Добавляем возможность запуска с параметрами командной строки
if __name__ == "__main__":
    start()
