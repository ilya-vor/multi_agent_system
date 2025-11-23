import argparse
import asyncio
from agent.agent import WorkerAgent
from common.backpack import load_backpack_from_file
from common.get_time import get_time


def build_parser():
    parser = argparse.ArgumentParser(description="Worker для распределённого распределения задач")
    parser.add_argument("--jid", required=True, help="JID работника")
    parser.add_argument("--password", required=True, help="Пароль")
    parser.add_argument("--backpack-file", required=True, help="Файл с данными задач (рюкзак)")
    parser.add_argument("--other_workers", nargs="+", help="JID известных работников")
    parser.add_argument("--specialization", help="Специализация работника (сварщик/слесарь/токарь)")
    parser.add_argument("--server", default="localhost", help="XMPP сервер")
    parser.add_argument("--save-interval", type=int, default=10, help="Интервал периодического сохранения")
    return parser


async def run_worker(args):
    backpack = load_backpack_from_file(args.backpack_file)
    worker = WorkerAgent(
        jid=args.jid,
        password=args.password,
        backpack_file=args.backpack_file,
        initial_items=backpack,
        other_workers=args.other_workers[0].split("+") if args.other_workers else [],
        specialization=args.specialization
    )

    await worker.start()
    print(f"Работник {args.jid} запущен. Ctrl+C для остановки")
    print(f"Файл задач: {args.backpack_file}.  Содержимое: {worker.backpack}")
