import json
from spade.behaviour import CyclicBehaviour
from common.get_time import get_time
from spade.message import Message


class WeightRequestBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if msg and msg.get_metadata("type") == "weight_request":
            try:
                # Отправляем наш текущий вес
                reply = msg.make_reply()
                reply.set_metadata("type", "weight_reply")
                self.agent.calculate_weight()
                reply.body = json.dumps({
                    "weight": self.agent.my_weight,
                    "task_count": len(self.agent.backpack),
                    "specialization": self.agent.specialization
                })
                await self.send(reply)
                print(
                    f"{get_time()} [WeightRequestBehaviour] {self.agent.jid}: Отправлен вес {self.agent.my_weight} для {msg.sender}")
            except Exception as e:
                print(f"{get_time()} [WeightRequestBehaviour] {self.agent.jid}: Ошибка обработки запроса веса: {e}")
                error_reply = msg.make_reply()
                error_reply.set_metadata("type", "weight_reply_error")
                error_reply.body = json.dumps({"error": str(e)})
                await self.send(error_reply)


class WeightReplyBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if (msg and
                msg.get_metadata("type") == "weight_reply" and
                msg.sender == self.agent.neighbor_choice):
            try:
                neighbor_data = json.loads(msg.body)
                neighbor_weight = neighbor_data.get("weight")
                neighbor_task_count = neighbor_data.get("task_count", 0)
                neighbor_specialization = neighbor_data.get("specialization")

                print(
                    f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Вес соседа {self.agent.neighbor_choice} = {neighbor_weight}, задач: {neighbor_task_count}, специализация: {neighbor_specialization}")

                # Шаг 4: Принятие решения
                average_weight = (self.agent.my_weight + neighbor_weight) / 2
                weight_diff = abs(self.agent.my_weight - neighbor_weight)
                threshold_value = self.agent.BALANCE_THRESHOLD * average_weight

                print(
                    f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Мой вес = {self.agent.my_weight:.2f}, вес соседа = {neighbor_weight:.2f}, порог = {threshold_value:.2f}")

                # Проверка сбалансированности
                if weight_diff <= threshold_value:
                    print(
                        f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Веса сбалансированы, завершаю раунд")
                    return

                # Если мой вес значительно больше
                if self.agent.my_weight > neighbor_weight + threshold_value:
                    print(
                        f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Мой вес больше, инициирую передачу объекта")

                    # Шаг 5: Выбор объекта для передачи
                    target_weight = average_weight
                    weight_to_shed = self.agent.my_weight - target_weight

                    # Предпочтение отдаем объектам, которые подходит по специализации получателя
                    # Сначала ищем объекты, которые и отправителю подходят по весу, и получателю по профессии
                    candidates = [item for item in self.agent.backpack if item["weight"] <= weight_to_shed]
                    compatible_for_neighbor = [item for item in candidates if "allowed_professions" in item and neighbor_specialization in item["allowed_professions"]]

                    if compatible_for_neighbor:
                        # выбрать ближайший по весу к weight_to_shed
                        self.agent.transfer_object = min(compatible_for_neighbor, key=lambda x: abs(x["weight"] - weight_to_shed))
                    else:
                        # fallback: выбрать объект, который сам отправитель может передать (без учёта получателя)
                        self.agent.transfer_object = self.agent.find_best_object_to_transfer(weight_to_shed)

                    if not self.agent.transfer_object:
                        print(f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Нет объектов для передачи")
                        return

                    # Если у отправителя одна задача и у соседа 0 задач — не передаём
                    if len(self.agent.backpack) == 1 and neighbor_task_count == 0:
                        print(f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Отмена передачи: у меня 1 задача, у соседа 0 задач")
                        self.agent.neighbor_choice = None
                        self.agent.transfer_object = None
                        return

                    print(
                        f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Выбран объект для передачи: {self.agent.transfer_object}")

                    # Шаг 6: Транзакция передачи
                    transfer_msg = Message(to=self.agent.neighbor_choice)
                    transfer_msg.set_metadata("type", "transfer_request")
                    transfer_msg.body = json.dumps({
                        "object": self.agent.transfer_object,
                        "expected_weight": self.agent.my_weight - self.agent.transfer_object["weight"]
                    })

                    await self.send(transfer_msg)
                    print(f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Отправлен запрос на передачу объекта")
                else:
                    self.agent.neighbor_choice = None
                    self.agent.transfer_object = None

            except Exception as e:
                self.agent.neighbor_choice = None
                self.agent.transfer_object = None
                print(f"{get_time()} [WeightReplyBehaviour] {self.agent.jid}: Ошибка: {e}")


class WeightReplyErrorBehaviour(CyclicBehaviour):
    """Обработка запросов веса от других агентов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if (msg and
                msg.get_metadata("type") == "weight_reply_error" and
                msg.sender == self.agent.neighbor_choice):
            neighbor_data = json.loads(msg.body)
            neighbor_error = neighbor_data["error"]
            print(f"{get_time()} [WeightReplyErrorBehaviour] {self.agent.jid}:"
                  f" {self.agent.neighbor_choice} ответил ошибкой {neighbor_error}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None