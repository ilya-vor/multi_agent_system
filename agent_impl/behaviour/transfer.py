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
                expected_time = data.get("expected_time", 0)

                print(f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                      f" Получен запрос на задачу {transfer_object}")

                # Добавляем объект в свой план
                self.agent.plan.append(transfer_object)
                self.agent.calculate_time()

                # Сохраняем план после получения объекта
                save_success = self.agent.save_plan()

                # Отправляем подтверждение
                confirm_msg = msg.make_reply()
                confirm_msg.set_metadata("type", "transfer_confirm")
                confirm_msg.body = json.dumps({
                    "received": True,
                    "new_time": self.agent.my_total_task_time,
                    "save_success": save_success
                })
                await self.send(confirm_msg)

                if save_success:
                    print(
                        f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                        f" Задача принята. Новый вес: {self.agent.my_total_task_time}. Рюкзак сохранен.")
                else:
                    print(
                        f"{get_time()} [TransferRequestBehaviour] {self.agent.jid}:"
                        f" Задача принята. Новый вес: {self.agent.my_total_task_time}. Ошибка сохранения рюкзака.")

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
            self.agent.neighbor_choice and
            confirm.sender == self.agent.neighbor_choice[0]):
            try:
                # Удаляем объект из своего плана
                self.agent.plan.remove(self.agent.transfer_object)
                print(
                    f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                    f" Объект удален: {self.agent.transfer_object}.")
                self.agent.calculate_time()

                # Сохраняем план после успешной передачи
                if self.agent.save_plan():
                    print(
                        f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                        f" Задача передана. Новые трудозатраты: {self.agent.my_total_task_time}. План сохранен.")
                else:
                    print(
                        f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                        f" Задача передана. Новые трудозатраты: {self.agent.my_total_task_time}. Ошибка сохранения плана.")
            except Exception as e:
                print(
                    f"{get_time()} [TransferConfirmBehaviour] {self.agent.jid}:"
                    f" Ошибка обработки подтверждения передачи: {e}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None
            self.agent.attempts_to_balancing = 5


class TransferConfirmErrorBehaviour(CyclicBehaviour):
    """Обработка запросов на передачу объектов"""

    async def run(self):
        confirm = await self.receive(timeout=10)
        if (confirm and
                confirm.get_metadata("type") == "transfer_confirm_error" and
                self.agent.neighbor_choice and
                confirm.sender == self.agent.neighbor_choice[0]):
            neighbor_data = json.loads(confirm.body)
            neighbor_error = neighbor_data["error"]
            print(
                f"{get_time()} [TransferConfirmErrorBehaviour] {self.agent.jid}:"
                f"{self.agent.neighbor_choice} ответил ошибкой {neighbor_error}")
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None