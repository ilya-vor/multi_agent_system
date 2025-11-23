import json
import random
from spade.behaviour import PeriodicBehaviour
from common.get_time import get_time
from spade.message import Message


class BalancingBehaviour(PeriodicBehaviour):
    async def run(self):
        """Основное поведение балансировки"""
        try:
            # Шаг 1: Сон уже реализован через PeriodicBehaviour

            # Шаг 2: Выбор случайного соседа
            if not self.agent.other_workers:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Нет других работников для балансировки")
                return

            # Избегаем запуска нескольких обменов для одного агента одновременно
            if self.agent.neighbor_choice is None:
                self.agent.neighbor_choice = random.choice(self.agent.other_workers)
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Выбран сосед {self.agent.neighbor_choice}")

                # Шаг 3: Обмен данными - запрос веса соседа
                self.agent.calculate_weight()

                msg = Message(to=self.agent.neighbor_choice)
                msg.set_metadata("type", "weight_request")
                msg.body = json.dumps({"weight": self.agent.my_weight})

                await self.send(msg)
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Отправлен запрос веса к {self.agent.neighbor_choice}")

        except Exception as e:
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None
            print(f"{get_time()} [BALANCE] {self.agent.jid}: Ошибка: {e}")