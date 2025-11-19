import argparse
import asyncio
from agent.agent import HikerAgent
from common.backpack import load_backpack_from_file
from common.get_time import get_time


async def main():
    parser = argparse.ArgumentParser(description="Турист для распределенной балансировки веса")
    parser.add_argument("--jid", required=True, help="JID туриста")
    parser.add_argument("--password", required=True, help="Пароль")
    parser.add_argument("--backpack-file", required=True, help="Файл с данными рюкзака")
    parser.add_argument("--other_hikers", nargs="+", help="JID известных туристов")
    parser.add_argument("--server", default="localhost", help="XMPP сервер")
    parser.add_argument("--save-interval", type=int, default=10, help="Интервал периодического сохранения")

    args = parser.parse_args()

    # Загружаем рюкзак
    backpack = load_backpack_from_file(args.backpack_file)

    # Создаем агента
    hiker = HikerAgent(
        jid=args.jid,
        password=args.password,
        backpack_file=args.backpack_file,
        initial_items=backpack,
        other_hikers=args.other_hikers[0].split("+") if args.other_hikers else []
    )

    try:
        await hiker.start()
        print(f"Турист {args.jid} запущен. Ctrl+C для остановки")
        print(f"Файл рюкзака: {args.backpack_file}.  Содержимое: {hiker.backpack}")

        # Периодическое сохранение (резервное)
        last_save = asyncio.get_event_loop().time()
        while True:
            await asyncio.sleep(1)
            current_time = asyncio.get_event_loop().time()
            if current_time - last_save >= args.save_interval:
                if hiker.save_backpack():
                    print(f"{get_time()} [PERIODIC SAVE] {hiker.jid}: Периодическое сохранение выполнено")
                else:
                    print(f"{get_time()} [PERIODIC SAVE] {hiker.jid}: Ошибка периодического сохранения")
                last_save = current_time

    except KeyboardInterrupt:
        print("Остановка...")
        # Финальное сохранение при остановке
        if hiker.save_backpack():
            print(f"{get_time()} [FINAL SAVE] {hiker.jid}: Финальное сохранение выполнено")
        else:
            print(f"{get_time()} [FINAL SAVE] {hiker.jid}: Ошибка финального сохранения")
        await hiker.stop()


if __name__ == "__main__":
    asyncio.run(main())