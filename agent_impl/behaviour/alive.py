import json
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from common.get_time import get_time
from spade.message import Message


class CheckAgentAlive(PeriodicBehaviour):
    async def run(self):
        try:
            if not self.agent.neighbor_choice is None:
                msg = Message(to=self.agent.neighbor_choice[0])
                msg.set_metadata("type", "request_alive")
                await self.send(msg)
                print(f"{get_time()} [CheckAgentAlive] {self.agent.jid}:"
                      f" Выполняю проверку связи с {self.agent.neighbor_choice}")
        except Exception as e:
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None
            print(f"{get_time()} [CheckAgentAlive] {self.agent.jid}: Ошибка: {e}")


class RequestAlive(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if msg and msg.get_metadata("type") == "request_alive":
            reply = msg.make_reply()
            reply.set_metadata("type", "reply_alive")
            await self.send(reply)
            print(f"{get_time()} [RequestAlive] {self.agent.jid}:"
                  f" Ответил агенту {msg.sender}")


class ReplyAlive(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if (msg and
                msg.get_metadata("type") == "reply_alive" and
                self.agent.neighbor_choice and
                msg.sender == self.agent.neighbor_choice[0]):
            pass
        else:
            self.agent.neighbor_choice = None
            self.agent.transfer_object = None
            print(f"{get_time()} [ReplyAlive] {self.agent.jid}:"
                  f" напарник не ответил, выбираем другого для обмена")