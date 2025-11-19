from spade.agent import Agent
from spade.template import Template

from agent.behaviour.alive import CheckAgentAlive, RequestAlive, ReplyAlive
from agent.behaviour.balancing import BalancingBehaviour
from agent.behaviour.transfer import TransferRequestBehaviour, TransferConfirmBehaviour, TransferConfirmErrorBehaviour
from agent.behaviour.weight import WeightRequestBehaviour, WeightReplyBehaviour, WeightReplyErrorBehaviour
from common.backpack import save_backpack_to_file, load_backpack_from_file
from common.get_time import get_time

# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )


class HikerAgent(Agent):
    def __init__(self, jid, password, backpack_file, other_hikers=None, initial_items=None):
        super().__init__(jid, password)
        self.COMMUNICATION_INTERVAL = 5
        self.BALANCE_THRESHOLD = 0.15
        self.transfer_object = None
        self.neighbor_choice = None
        self.my_weight = None
        self.backpack = initial_items if initial_items else []
        self.backpack_file = backpack_file
        self.other_hikers = other_hikers if other_hikers else []
        self.total_weight = sum(item["weight"] for item in self.backpack)

    async def setup(self):
        print(
            f"{get_time()} [SETUP] {self.jid} запущен. Начальный вес: {self.total_weight}, файл: {self.backpack_file}")

        # Шаблоны для различных типов сообщений
        request_agent_alive = Template()
        request_agent_alive.set_metadata("type", "request_alive")
        replay_agent_alive = Template()
        replay_agent_alive.set_metadata("type", "replay_alive")
        weight_request_template = Template()
        weight_request_template.set_metadata("type", "weight_request")
        weight_reply_template = Template()
        weight_reply_template.set_metadata("type", "weight_reply")
        weight_reply_error_template = Template()
        weight_reply_error_template.set_metadata("type", "weight_reply_error")
        transfer_request_template = Template()
        transfer_request_template.set_metadata("type", "transfer_request")
        transfer_confirm_template = Template()
        transfer_confirm_template.set_metadata("type", "transfer_confirm")
        transfer_confirm_error_template = Template()
        transfer_confirm_error_template.set_metadata("type", "transfer_confirm_error")

        # Добавляем поведения
        self.add_behaviour(CheckAgentAlive(period=self.COMMUNICATION_INTERVAL))
        self.add_behaviour(RequestAlive(), template=request_agent_alive)
        self.add_behaviour(ReplyAlive(), template=replay_agent_alive)

        self.add_behaviour(BalancingBehaviour(period=self.COMMUNICATION_INTERVAL))
        self.add_behaviour(WeightRequestBehaviour(), template=weight_request_template)
        self.add_behaviour(WeightReplyBehaviour(), template=weight_reply_template)
        self.add_behaviour(WeightReplyErrorBehaviour(), template=weight_reply_error_template)
        self.add_behaviour(TransferRequestBehaviour(), template=transfer_request_template)
        self.add_behaviour(TransferConfirmBehaviour(), template=transfer_confirm_template)
        self.add_behaviour(TransferConfirmErrorBehaviour(), template=transfer_confirm_error_template)

    def calculate_weight(self):
        """Пересчитывает общий вес рюкзака"""
        self.my_weight = sum(item["weight"] for item in self.backpack)
        return self.my_weight

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