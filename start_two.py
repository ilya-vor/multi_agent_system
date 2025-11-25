import asyncio
from agent_impl.agent import WorkerAgent
from common.get_time import get_time

async def main():
    workers = []
    current_jid =  "worker1@26.3.185.180" # jid текущего агента
    current_specializations =  [
          "программист",
          "тестировщик"
        ] # специализации текущего агента
    other_agents = [["worker2@26.3.185.180", ["программист"]], ["worker3@26.3.185.180", ["тестировщик"]], ["worker4@26.3.185.180", ["программист", "тестировщик"]]]
    w = WorkerAgent(
        jid=current_jid,
        password=current_jid.split("@")[0],
        plan_file="plans\\old\\worker1.json",
        other_agents=other_agents,
        specializations=current_specializations,
    )
    workers.append(w)

    current_jid =  "worker2@26.3.185.180" # jid текущего агента
    current_specializations =  [
          "программист"
        ] # специализации текущего агента
    other_agents = [["worker1@26.3.185.180", ["программист", "тестировщик"]], ["worker3@26.3.185.180", ["тестировщик"]], ["worker4@26.3.185.180", ["программист", "тестировщик"]]]
    w = WorkerAgent(
        jid=current_jid,
        password=current_jid.split("@")[0],
        plan_file="plans\\old\\worker2.json",
        other_agents=other_agents,
        specializations=current_specializations,
    )
    workers.append(w)

        # start all
    for w in workers:
        await w.start()
        print(f"{get_time()} Started {w.jid}")

    print("All agents started; press Ctrl+C to stop")
    while True:
        await asyncio.sleep(workers[0].COMMUNICATION_INTERVAL)
        for w in workers:
            if w.save_plan():
                print(f"{get_time()} [PERIODIC SAVE] {w.jid}: Периодическое сохранение выполнено")
            else:
                print(f"{get_time()} [PERIODIC SAVE] {w.jid}: Ошибка периодического сохранения")


if __name__ == "__main__":
    asyncio.run(main())