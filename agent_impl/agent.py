from spade.agent import Agent
from spade.template import Template
from agent_impl.behaviour.alive import CheckAgentAlive, RequestAlive, ReplyAlive
from agent_impl.behaviour.balancing import BalancingBehaviour
from agent_impl.behaviour.transfer import TransferRequestBehaviour, TransferConfirmBehaviour, TransferConfirmErrorBehaviour
from agent_impl.behaviour.time import TimeRequestBehaviour, TimeReplyBehaviour, TimeReplyErrorBehaviour
from common.plan_load_save import save_plan_to_file, load_plan_from_file
from common.get_time import get_time

# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )


class WorkerAgent(Agent):
    def __init__(self, jid, password, plan_file, other_agents=None, specializations = None, my_total_task_time = None):
        super().__init__(jid, password)
        self.COMMUNICATION_INTERVAL = 5
        self.BALANCE_THRESHOLD = 0.15
        self.transfer_object = None
        self.neighbor_choice = None
        self.my_total_task_time = my_total_task_time
        self.plan_file = plan_file
        self.other_agents = other_agents if other_agents else []
        self.specializations = specializations if specializations else []
        self.plan = []
        self.attempts_to_balancing = 10


    async def setup(self):
        self.load_plan()
        print(
            f"{get_time()} [SETUP] {self.jid} запущен."
            f" Начальное время на выполнение всех задач: {self.my_total_task_time}, файл: {self.plan_file}")

        # Шаблоны для различных типов сообщений
        request_agent_alive = Template()
        request_agent_alive.set_metadata("type", "request_alive")
        replay_agent_alive = Template()
        replay_agent_alive.set_metadata("type", "replay_alive")
        time_request_template = Template()
        time_request_template.set_metadata("type", "time_request")
        time_reply_template = Template()
        time_reply_template.set_metadata("type", "time_reply")
        time_reply_error_template = Template()
        time_reply_error_template.set_metadata("type", "time_reply_error")
        transfer_request_template = Template()
        transfer_request_template.set_metadata("type", "transfer_request")
        transfer_confirm_template = Template()
        transfer_confirm_template.set_metadata("type", "transfer_confirm")
        transfer_confirm_error_template = Template()
        transfer_confirm_error_template.set_metadata("type", "transfer_confirm_error")

        # Добавляем поведения
        self.add_behaviour(CheckAgentAlive(period=self.COMMUNICATION_INTERVAL * 1.5))
        self.add_behaviour(RequestAlive(), template=request_agent_alive)
        self.add_behaviour(ReplyAlive(), template=replay_agent_alive)

        self.add_behaviour(BalancingBehaviour(period=self.COMMUNICATION_INTERVAL))
        self.add_behaviour(TimeRequestBehaviour(), template=time_request_template)
        self.add_behaviour(TimeReplyBehaviour(), template=time_reply_template)
        self.add_behaviour(TimeReplyErrorBehaviour(), template=time_reply_error_template)
        self.add_behaviour(TransferRequestBehaviour(), template=transfer_request_template)
        self.add_behaviour(TransferConfirmBehaviour(), template=transfer_confirm_template)
        self.add_behaviour(TransferConfirmErrorBehaviour(), template=transfer_confirm_error_template)

    def calculate_time(self):
        """Пересчитывает общий вес рюкзака"""
        self.my_total_task_time = sum(item["time"] for item in self.plan)
        return self.my_total_task_time

    def save_plan(self):
        """Сохраняет текущий рюкзак в файл"""
        return save_plan_to_file(self.plan_file, self.plan)

    def load_plan(self):
        self.plan = load_plan_from_file(self.plan_file)
        self.calculate_time()

    def find_best_object_to_transfer(self, time_to_shed):
        suitable_objects = [
            item for item in self.plan
            if item["time"] < time_to_shed
               and all(spec in self.neighbor_choice[1] for spec in item["specializations"])
        ]

        if not suitable_objects:
            return None

        # Находим объект с весом, наиболее близким к time_to_shed
        best_object = min(suitable_objects, key=lambda x: abs(x["time"] - time_to_shed))
        return best_object