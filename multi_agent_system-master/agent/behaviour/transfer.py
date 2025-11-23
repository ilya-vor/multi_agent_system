import json
from spade.behaviour import CyclicBehaviour
from common.get_time import get_time


class TransferRequestBehaviour(CyclicBehaviour):
    """Обработка запросов на передачу объектов"""

    async def run(self):
        msg = await self.receive(timeout=10)
        if msg and msg.get_metadata("type") == "transfer_request":
            try:
                data = json.loads(msg.body)
                transfer_object = data["object"]
                expected_weight = data.get("expected_weight", 0)

                print(f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                      f" Получен запрос на объект {transfer_object}")

                # Добавляем объект в свой рюкзак
                # Проверка специализации: может ли этот агент выполнить задачу?
                allowed = transfer_object.get("allowed_professions")
                if allowed and self.agent.specialization not in allowed:
                    raise Exception(f"specialization_mismatch: {self.agent.specialization} not in {allowed}")

                self.agent.backpack.append(transfer_object)
                self.agent.calculate_weight()

                # Сохраняем рюкзак после получения объекта
                save_success = self.agent.save_backpack()

                # Отправляем подтверждение
                confirm_msg = msg.make_reply()
                confirm_msg.set_metadata("type", "transfer_confirm")
                confirm_msg.body = json.dumps({
                    "received": True,
                    "new_weight": self.agent.my_weight,
                    "save_success": save_success
                })
                await self.send(confirm_msg)

                if save_success:
                    print(
                        f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                        f" Объект принят. Новый вес: {self.agent.my_weight}. Рюкзак сохранен.")
                else:
                    print(
                        f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                        f" Объект принят. Новый вес: {self.agent.my_weight}. Ошибка сохранения рюкзака.")

            except Exception as e:
                print(
                    f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                    f" Ошибка обработки запроса передачи: {e}")
                # Отправляем отказ
                error_reply = msg.make_reply()
                error_reply.set_metadata("type", "transfer_confirm_error")
                error_reply.body = json.dumps({"error": str(e)})
                await self.send(error_reply)


class TransferConfirmBehaviour(CyclicBehaviour):
    """Обработка запросов на передачу объектов"""

    async def run(self):
        confirm = await self.receive(timeout=10)
        if (confirm and
            confirm.get_metadata("type") == "transfer_confirm" and
            confirm.sender == self.agent.neighbor_choice):
            try:
                # Удаляем объект из своего рюкзака
                self.agent.backpack.remove(self.agent.transfer_object)
                print(
                    f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                    f" Объект удален: {self.agent.transfer_object}.")
                self.agent.calculate_weight()

                # Сохраняем рюкзак после успешной передачи
                if self.agent.save_backpack():
                    print(
                        f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                        f" Объект передан. Новый вес: {self.agent.my_weight}. Рюкзак сохранен.")
                else:
                    print(
                        f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                        f" Объект передан. Новый вес: {self.agent.my_weight}. Ошибка сохранения рюкзака.")
            except Exception as e:
                print(
                    f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                    f" Ошибка обработки подтверждения передачи: {e}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None


class TransferConfirmErrorBehaviour(CyclicBehaviour):
    """Обработка запросов на передачу объектов"""

    async def run(self):
        confirm = await self.receive(timeout=10)
        if (confirm and
                confirm.get_metadata("type") == "transfer_confirm_error" and
                confirm.sender == self.agent.neighbor_choice):
            neighbor_data = json.loads(confirm.body)
            neighbor_error = neighbor_data["error"]
            print(
                f"{get_time()} [TransferConfirmErrorBehaviour] {self.agent.jid}:"
                f"{self.agent.neighbor_choice} ответил ошибкой {neighbor_error}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None