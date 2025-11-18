import argparse
import logging
import asyncio
import random
import time
from datetime import datetime

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template
import json

# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )

# Константы алгоритма
COMMUNICATION_INTERVAL = 5  # секунды
BALANCE_THRESHOLD = 0.15  # 15% порог разницы

def get_time():
    timestamp = time.time()
    return datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]

def load_backpack_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("backpack", [])
    except Exception as e:
        print(f"Ошибка загрузки {file_path}: {e}")
        return []


def save_backpack_to_file(file_path, backpack):
    try:
        data = {
            "backpack": backpack,
            "total_weight": sum(item["weight"] for item in backpack)
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{get_time()} [SAVE] Рюкзак сохранен в {file_path}, вес: {data['total_weight']}")
        return True
    except Exception as e:
        print(f"{get_time()} [SAVE] Ошибка сохранения {file_path}: {e}")
        return False


class HikerAgent(Agent):
    def __init__(self, jid, password, backpack_file, other_hikers=None, initial_items=None):
        super().__init__(jid, password)
        self.backpack = initial_items if initial_items else []
        self.backpack_file = backpack_file
        self.other_hikers = other_hikers if other_hikers else []
        self.total_weight = sum(item["weight"] for item in self.backpack)

    async def setup(self):
        print(f"{get_time()} [SETUP] {self.jid} запущен. Начальный вес: {self.total_weight}, файл: {self.backpack_file}")

        # Шаблоны для различных типов сообщений
        weight_request_template = Template()
        weight_request_template.set_metadata("type", "weight_request")

        weight_reply_template = Template()
        weight_reply_template.set_metadata("type", "weight_reply")

        transfer_request_template = Template()
        transfer_request_template.set_metadata("type", "transfer_request")

        transfer_confirm_template = Template()
        transfer_confirm_template.set_metadata("type", "transfer_confirm")

        # Добавляем поведения
        self.add_behaviour(self.BalancingBehaviour(period=COMMUNICATION_INTERVAL))
        self.add_behaviour(self.WeightRequestBehaviour(), template=weight_request_template)
        self.add_behaviour(self.WeightReplyBehaviour(), template=weight_request_template)
        self.add_behaviour(self.TransferRequestBehaviour(), template=transfer_request_template)
        self.add_behaviour(self.TransferConfirmBehaviour(), template=transfer_request_template)

    def calculate_weight(self):
        """Пересчитывает общий вес рюкзака"""
        self.total_weight = sum(item["weight"] for item in self.backpack)
        return self.total_weight

    def save_backpack(self):
        """Сохраняет текущий рюкзак в файл"""
        return save_backpack_to_file(f"{self.backpack_file}_new", self.backpack)

    def find_best_object_to_transfer(self, weight_to_shed):
        """
        Находит лучший объект для передачи
        Цель: объект с весом, наиболее близким к weight_to_shed, но не превышающим его
        """
        # Фильтруем объекты, которые можно передать (вес <= weight_to_shed)
        suitable_objects = [item for item in self.backpack if item["weight"] <= weight_to_shed]

        if not suitable_objects:
            # Если нет подходящих объектов, возвращаем самый легкий
            return min(self.backpack, key=lambda x: x["weight"]) if self.backpack else None

        # Находим объект с весом, наиболее близким к weight_to_shed
        best_object = min(suitable_objects,
                          key=lambda x: abs(x["weight"] - weight_to_shed))
        return best_object

    class BalancingBehaviour(PeriodicBehaviour):
        async def run(self):
            """Основное поведение балансировки"""
            # Шаг 1: Сон уже реализован через PeriodicBehaviour

            # Шаг 2: Выбор случайного соседа
            if not self.agent.other_hikers:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Нет других туристов для балансировки")
                return

            neighbor = random.choice(self.agent.other_hikers)
            print(f"{get_time()} [BALANCE] {self.agent.jid}: Выбран сосед {neighbor}")

            # Шаг 3: Обмен данными - запрос веса соседа
            my_weight = self.agent.calculate_weight()

            msg = Message(to=neighbor)
            msg.set_metadata("type", "weight_request")
            msg.body = json.dumps({"weight": my_weight})

            await self.send(msg)
            print(f"{get_time()} [BALANCE] {self.agent.jid}: Отправлен запрос веса к {neighbor}")

            # Ждем ответа
            reply = await self.receive(timeout=10)
            if not reply:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Таймаут ответа от {neighbor}")
                return

            if reply.get_metadata("type") != "weight_reply":
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Неверный тип ответа от {neighbor}")
                return

            try:
                neighbor_data = json.loads(reply.body)
                neighbor_weight = neighbor_data["weight"]
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Вес соседа {neighbor} = {neighbor_weight}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Ошибка парсинга ответа: {e}")
                return

            # Шаг 4: Принятие решения
            average_weight = (my_weight + neighbor_weight) / 2
            weight_diff = abs(my_weight - neighbor_weight)
            threshold_value = BALANCE_THRESHOLD * average_weight

            print(
                f"{get_time()} [BALANCE] {self.agent.jid}: Средний вес = {average_weight:.2f}, разница = {weight_diff:.2f}, порог = {threshold_value:.2f}")

            # Проверка сбалансированности
            if weight_diff <= threshold_value:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Веса сбалансированы, завершаю раунд")
                return

            # Если мой вес значительно больше
            if my_weight > neighbor_weight + threshold_value:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Мой вес больше, инициирую передачу объекта")

                # Шаг 5: Выбор объекта для передачи
                target_weight = average_weight
                weight_to_shed = my_weight - target_weight

                candidate_object = self.agent.find_best_object_to_transfer(weight_to_shed)

                if not candidate_object:
                    print(f"{get_time()} [BALANCE] {self.agent.jid}: Нет объектов для передачи")
                    return

                print(f"{get_time()} [BALANCE] {self.agent.jid}: Выбран объект для передачи: {candidate_object}")

                # Шаг 6: Транзакция передачи
                transfer_msg = Message(to=neighbor)
                transfer_msg.set_metadata("type", "transfer_request")
                transfer_msg.body = json.dumps({
                    "object": candidate_object,
                    "expected_weight": my_weight - candidate_object["weight"]
                })

                await self.send(transfer_msg)
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Отправлен запрос на передачу объекта")

                # Ждем подтверждения
                confirm = await self.receive(timeout=10)
                if (confirm and
                        confirm.get_metadata("type") == "transfer_confirm" and
                        confirm.sender == neighbor):
                    # Удаляем объект из своего рюкзака
                    self.agent.backpack.remove(candidate_object)
                    print(f"{get_time()} [BALANCE] {self.agent.jid}: Объект удален: {candidate_object}.")
                    new_weight = self.agent.calculate_weight()

                    # Сохраняем рюкзак после успешной передачи
                    if self.agent.save_backpack():
                        print(f"{get_time()} [BALANCE] {self.agent.jid}: Объект передан. Новый вес: {new_weight}. Рюкзак сохранен.")
                    else:
                        print(
                            f"{get_time()} [BALANCE] {self.agent.jid}: Объект передан. Новый вес: {new_weight}. Ошибка сохранения рюкзака.")
                else:
                    print(f"{get_time()} [BALANCE] {self.agent.jid}: Подтверждение не получено, объект не передан")

            # Если мой вес значительно меньше - пассивно ждем, когда сосед предложит объекты
            elif my_weight < neighbor_weight - threshold_value:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Мой вес меньше, жду предложений от соседа")
                # В классическом алгоритме агент пассивно ждет, когда донор сам предложит объекты

    class WeightRequestBehaviour(CyclicBehaviour):
        """Обработка запросов веса от других агентов"""

        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("type") == "weight_request":
                try:
                    # Отправляем наш текущий вес
                    reply = msg.make_reply()
                    reply.set_metadata("type", "weight_reply")
                    current_weight = self.agent.calculate_weight()
                    reply.body = json.dumps({"weight": current_weight})
                    await self.send(reply)
                    print(f"{get_time()} [WEIGHT] {self.agent.jid}: Отправлен вес {current_weight} для {msg.sender}")
                except Exception as e:
                    print(f"{get_time()} [WEIGHT] {self.agent.jid}: Ошибка обработки запроса веса: {e}")

    class WeightReplyBehaviour(CyclicBehaviour):
        """Обработка запросов веса от других агентов"""

        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("type") == "weight_request":
                try:
                    # Отправляем наш текущий вес
                    reply = msg.make_reply()
                    reply.set_metadata("type", "weight_reply")
                    current_weight = self.agent.calculate_weight()
                    reply.body = json.dumps({"weight": current_weight})
                    await self.send(reply)
                    print(f"{get_time()} [WEIGHT] {self.agent.jid}: Отправлен вес {current_weight} для {msg.sender}")
                except Exception as e:
                    print(f"{get_time()} [WEIGHT] {self.agent.jid}: Ошибка обработки запроса веса: {e}")

    class TransferRequestBehaviour(CyclicBehaviour):
        """Обработка запросов на передачу объектов"""

        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("type") == "transfer_request":
                try:
                    data = json.loads(msg.body)
                    transfer_object = data["object"]
                    expected_weight = data.get("expected_weight", 0)

                    print(f"{get_time()} [TRANSFER] {self.agent.jid}: Получен запрос на объект {transfer_object}")

                    # Добавляем объект в свой рюкзак
                    self.agent.backpack.append(transfer_object)
                    new_weight = self.agent.calculate_weight()

                    # Сохраняем рюкзак после получения объекта
                    save_success = self.agent.save_backpack()

                    # Отправляем подтверждение
                    confirm_msg = msg.make_reply()
                    confirm_msg.set_metadata("type", "transfer_confirm")
                    confirm_msg.body = json.dumps({
                        "received": True,
                        "new_weight": new_weight,
                        "save_success": save_success
                    })
                    await self.send(confirm_msg)

                    if save_success:
                        print(f"{get_time()} [TRANSFER] {self.agent.jid}: Объект принят. Новый вес: {new_weight}. Рюкзак сохранен.")
                    else:
                        print(
                            f"{get_time()} [TRANSFER] {self.agent.jid}: Объект принят. Новый вес: {new_weight}. Ошибка сохранения рюкзака.")

                except Exception as e:
                    print(f"{get_time()} [TRANSFER] {self.agent.jid}: Ошибка обработки запроса передачи: {e}")
                    # Отправляем отказ
                    error_reply = msg.make_reply()
                    error_reply.set_metadata("type", "transfer_error")
                    error_reply.body = json.dumps({"error": str(e)})
                    await self.send(error_reply)

    class TransferConfirmBehaviour(CyclicBehaviour):
        """Обработка запросов на передачу объектов"""

        async def run(self):
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("type") == "transfer_request":
                try:
                    data = json.loads(msg.body)
                    transfer_object = data["object"]
                    expected_weight = data.get("expected_weight", 0)

                    print(f"{get_time()} [TRANSFER] {self.agent.jid}: Получен запрос на объект {transfer_object}")

                    # Добавляем объект в свой рюкзак
                    self.agent.backpack.append(transfer_object)
                    new_weight = self.agent.calculate_weight()

                    # Сохраняем рюкзак после получения объекта
                    save_success = self.agent.save_backpack()

                    # Отправляем подтверждение
                    confirm_msg = msg.make_reply()
                    confirm_msg.set_metadata("type", "transfer_confirm")
                    confirm_msg.body = json.dumps({
                        "received": True,
                        "new_weight": new_weight,
                        "save_success": save_success
                    })
                    await self.send(confirm_msg)

                    if save_success:
                        print(f"{get_time()} [TRANSFER] {self.agent.jid}: Объект принят. Новый вес: {new_weight}. Рюкзак сохранен.")
                    else:
                        print(
                            f"{get_time()} [TRANSFER] {self.agent.jid}: Объект принят. Новый вес: {new_weight}. Ошибка сохранения рюкзака.")

                except Exception as e:
                    print(f"{get_time()} [TRANSFER] {self.agent.jid}: Ошибка обработки запроса передачи: {e}")
                    # Отправляем отказ
                    error_reply = msg.make_reply()
                    error_reply.set_metadata("type", "transfer_error")
                    error_reply.body = json.dumps({"error": str(e)})
                    await self.send(error_reply)


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