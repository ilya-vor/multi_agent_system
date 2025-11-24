import json
from spade.behaviour import CyclicBehaviour
from common.get_time import get_time
from spade.message import Message


class TimeRequestBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if msg and msg.get_metadata("type") == "time_request":
            try:
                # Отправляем наш текущий вес
                reply = msg.make_reply()
                reply.set_metadata("type", "time_reply")
                self.agent.calculate_time()
                reply.body = json.dumps({"time": self.agent.my_total_task_time})
                await self.send(reply)
                print(
                    f"{get_time()} [TimeRequestBehaviour] {self.agent.jid}: Отправлен вес {self.agent.my_total_task_time} для {msg.sender}")
            except Exception as e:
                print(f"{get_time()} [TimeRequestBehaviour] {self.agent.jid}: Ошибка обработки запроса веса: {e}")
                error_reply = msg.make_reply()
                error_reply.set_metadata("type", "time_reply_error")
                error_reply.body = json.dumps({"error": str(e)})
                await self.send(error_reply)


class TimeReplyBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if (msg and
                msg.get_metadata("type") == "time_reply" and
                self.agent.neighbor_choice and
                msg.sender == self.agent.neighbor_choice[0]):
            try:
                neighbor_data = json.loads(msg.body)
                neighbor_time = neighbor_data["time"]
                print(f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}:"
                      f" Трудозатраты соседа {self.agent.neighbor_choice} = {neighbor_time}")

                # Шаг 4: Принятие решения
                average_time = (self.agent.my_total_task_time + neighbor_time) / 2
                time_diff = abs(self.agent.my_total_task_time - neighbor_time)
                threshold_value = self.agent.BALANCE_THRESHOLD * average_time

                print(
                    f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}:"
                    f" Мой вес = {self.agent.my_total_task_time:.2f}, вес соседа = {neighbor_time:.2f}, порог = {threshold_value:.2f}")

                # Проверка сбалансированности
                if time_diff <= threshold_value:
                    print(
                        f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}: Задачи сбалансированы, завершаю раунд")
                    self.agent.attempts_to_balancing -= 1
                    return

                # Если мой вес значительно больше
                if self.agent.my_total_task_time > neighbor_time + threshold_value:
                    print(
                        f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}:"
                        f" У меня задач больше, инициирую передачу задачи")

                    # Шаг 5: Выбор объекта для передачи
                    target_time = average_time
                    time_to_shed = self.agent.my_total_task_time - target_time + threshold_value

                    self.agent.transfer_object = self.agent.find_best_object_to_transfer(time_to_shed)

                    if not self.agent.transfer_object:
                        print(f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}: Нет задач для передачи")
                        self.agent.neighbor_choice = None
                        return

                    print(
                        f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}: Выбрана задача для передачи: {self.agent.transfer_object}")

                    # Шаг 6: Транзакция передачи
                    transfer_msg = Message(to=self.agent.neighbor_choice[0])
                    transfer_msg.set_metadata("type", "transfer_request")
                    transfer_msg.body = json.dumps({
                        "object": self.agent.transfer_object,
                        "expected_time": self.agent.my_total_task_time - self.agent.transfer_object["time"]
                    })

                    await self.send(transfer_msg)
                    print(f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}: Отправлен запрос на передачу задачи")
                else:
                    self.agent.attempts_to_balancing -= 1
                    self.agent.neighbor_choice = None
                    self.agent.transfer_object = None

            except Exception as e:
                self.agent.neighbor_choice = None
                self.agent.transfer_object = None
                print(f"{get_time()} [TimeReplyBehaviour] {self.agent.jid}: Ошибка: {e}")


class TimeReplyErrorBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if (msg and
                msg.get_metadata("type") == "time_reply_error" and
                self.agent.neighbor_choice and
                msg.sender == self.agent.neighbor_choice[0]):
            neighbor_data = json.loads(msg.body)
            neighbor_error = neighbor_data["error"]
            print(f"{get_time()} [TimeReplyErrorBehaviour] {self.agent.jid}:"
                  f" {self.agent.neighbor_choice} ответил ошибкой {neighbor_error}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None