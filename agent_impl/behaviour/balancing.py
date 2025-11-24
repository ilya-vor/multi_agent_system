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
            if not self.agent.other_agents:
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Нет других агентов для балансировки")
                return

            # Избегаем запуска нескольких обменов для одного агента одновременно
            if self.agent.neighbor_choice is None:
                # Получаем все уникальные специализации из плана
                all_specializations = set()
                for task in self.agent.plan:
                    all_specializations.update(task['specializations'])

                # Выбираем случайную специализацию
                if all_specializations:
                    chosen_specialization = random.choice(list(all_specializations))

                    # Фильтруем other_agents по выбранной специализации
                    matching_agents = []
                    for agent_info in self.agent.other_agents:
                        if chosen_specialization in agent_info[1]:
                            matching_agents.append(agent_info)

                    # Если есть подходящие агенты - выбираем случайного
                    if matching_agents:
                        self.agent.neighbor_choice = random.choice(matching_agents)
                    else:
                        return  # нет подходящих агентов
                else:
                    return  # нет специализаций в плане

                print(f"{get_time()} [BALANCE] {self.agent.jid}: Выбран сосед {self.agent.neighbor_choice}")

                # Шаг 3: Обмен данными - запрос веса соседа
                self.agent.calculate_time()

                msg = Message(to=self.agent.neighbor_choice[0])
                msg.set_metadata("type", "time_request")
                msg.body = json.dumps({"weight": self.agent.my_total_task_time})

                await self.send(msg)
                print(f"{get_time()} [BALANCE] {self.agent.jid}: Отправлен запрос трудозатрат к {self.agent.neighbor_choice}")

        except Exception as e:
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None
            print(f"{get_time()} [BALANCE] {self.agent.jid}: Ошибка: {e}")