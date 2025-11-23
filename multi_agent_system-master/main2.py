import sys


async def start():
    # Параметры для подключения
    params = [
        "--jid", "worker2@26.3.185.180",
        "--password", "worker2",
        "--backpack-file", "backpacks/old/backpack2.json",
        "--other_workers", "worker1@26.3.185.180+worker3@26.3.185.180+worker4@26.3.185.180",
        "--server", "26.3.185.180",
        "--specialization", "слесарь"
    ]

    # Подменяем sys.argv для передачи параметров
    sys.argv = [sys.argv[0]] + params

    # Импортируем и запускаем основной модуль
    import main

    # Для отладчика - устанавливаем точку останова здесь
    print("Запуск агента worker2...")
    await main.main()


# Добавляем возможность запуска с параметрами командной строки
if __name__ == "__main__":
    start()
