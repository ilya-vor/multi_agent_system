import sys
import argparse
import json
import asyncio
from pathlib import Path
from agent_impl.agent import WorkerAgent
from common.get_time import get_time
import random
import json
import os
import shutil


def load_json(p: Path):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def distribute_tasks(agents_data, tasks):
    # Prepare per-agent backpacks and current total weights
    agent_map = {}
    for a in agents_data:
        agent_map[a['jid']] = {
            'agent': a,
            'tasks': [],
            'total_task_time': 0.0
        }

    # For each task, try to assign to an agent whose specialization is allowed
    for t in tasks:
        task_spec = t.get('specializations')
        if task_spec:
            # Получаем все элементы agent_map и перемешиваем их в случайном порядке
            agent_items = list(agent_map.items())
            random.shuffle(agent_items)

            for jid, agent_data in agent_items:
                agent_spec = agent_data["agent"].get('specializations')
                if all(spec in agent_spec for spec in task_spec):
                    # Добавляем задачу агенту
                    agent_map[jid]['tasks'].append(t)
                    # Обновляем общее время задач агента
                    task_time = t.get('time', 0)  # предполагаем, что у задачи есть поле 'time'
                    agent_map[jid]['total_task_time'] += task_time
                    break

    # Очищаем папку plans/old/ и сохраняем данные агентов
    old_plans_dir = 'plans/old'

    # Создаем папку, если она не существует
    if not os.path.exists(old_plans_dir):
        os.makedirs(old_plans_dir)

    # Очищаем содержимое папки
    for filename in os.listdir(old_plans_dir):
        file_path = os.path.join(old_plans_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Ошибка при удалении {file_path}: {e}")

    # Сохраняем информацию каждого агента в отдельный JSON файл
    result_dict = {}
    for jid, agent_data in agent_map.items():
        filename = f"{jid.split('@')[0]}.json"
        file_path = os.path.join(old_plans_dir, filename)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(agent_data, f, ensure_ascii=False, indent=2)

            total_task_time = agent_data['total_task_time']
            # Добавляем информацию в результирующий словарь
            result_dict[jid] = [
                jid,  # jid агента
                agent_data['agent'].get('specializations', []),  # специализации агента
                file_path,  # путь к файлу
                total_task_time
            ]
        except Exception as e:
            print(f"Ошибка при сохранении файла {file_path}: {e}")

    return result_dict


async def main():
    parser = argparse.ArgumentParser(description='Start all agents from data files and distribute tasks')
    parser.add_argument('--agents-file', default='common/agents.json')
    parser.add_argument('--tasks-file', default='common/tasks.json')
    args = parser.parse_args()

    agents_path = Path(args.agents_file)
    tasks_path = Path(args.tasks_file)

    if not agents_path.exists():
        print(f'Agents file not found: {agents_path}')
        agents_path = "agents.json"
    if not tasks_path.exists():
        print(f'Tasks file not found: {tasks_path}')
        tasks_path = "tasks.json"

    agents = load_json(agents_path)
    tasks = load_json(tasks_path)

    result_dict = distribute_tasks(agents, tasks)

    print(f"{get_time()} Loaded {len(agents)} agents and {len(tasks)} tasks")

    # Instantiate and start all agents
    workers = []

    for jid, agent_info in result_dict.items():
        current_jid = agent_info[0]  # jid текущего агента
        current_specializations = agent_info[1]  # специализации текущего агента
        other_agents = []
        for other_jid, other_agent_info in result_dict.items():
            if other_jid != jid:  # исключаем текущего агента
                other_agents.append([
                    other_agent_info[0],  # jid другого агента
                    other_agent_info[1]  # специализации другого агента
                ])
        w = WorkerAgent(
            jid=current_jid,
            password=current_jid.split('@')[0],
            plan_file=agent_info[2],
            other_agents=other_agents,
            specializations=current_specializations,
            my_total_task_time=agent_info[3]
        )
        workers.append(w)

    try:
        # start all
        for w in workers:
            await w.start()
            print(f"{get_time()} Started {w.jid}")

        print('All agents started; press Ctrl+C to stop')
        while True:
            await asyncio.sleep(workers[0].COMMUNICATION_INTERVAL)
            for w in workers:
                if w.save_plan():
                    print(f"{get_time()} [PERIODIC SAVE] {w.jid}: Периодическое сохранение выполнено")
                else:
                    print(f"{get_time()} [PERIODIC SAVE] {w.jid}: Ошибка периодического сохранения")

    except KeyboardInterrupt:
        print('Stopping agents...')
        for w in workers:
            await w.stop()


if __name__ == '__main__':
    asyncio.run(main())