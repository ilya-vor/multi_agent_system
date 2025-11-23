import json
import random
import asyncio
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
                # Небольшая случайная задержка при старте, чтобы уменьшить вероятность гонки
                await asyncio.sleep(random.uniform(0.2, 1.0))

                # Попробуем выбрать соседа, который может принять хотя бы один объект из нашего рюкзака
                chosen = None
                try:
                    for neighbor in random.sample(self.agent.other_workers, len(self.agent.other_workers)):
                        info = self.agent.known_neighbors.get(neighbor)
                        if not info or not self.agent.backpack:
                            continue
                        neigh_spec = info.get("specialization")
                        if not neigh_spec:
                            continue
                        # если у нас есть хоть один объект, который сосед может выполнить
                        for item in self.agent.backpack:
                            allowed = item.get("allowed_professions")
                            if allowed and neigh_spec in allowed:
                                chosen = neighbor
                                break
                        if chosen:
                            break
                except Exception:
                    chosen = None

                if not chosen:
                    # fallback: случайный сосед
                    chosen = random.choice(self.agent.other_workers)

                self.agent.neighbor_choice = chosen
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