import asyncio
import json
import argparse
from pathlib import Path
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template


class HikerAgent(Agent):
    def __init__(self, jid, password, initial_items=None):
        super().__init__(jid, password)
        self.backpack = initial_items if initial_items else []

    async def setup(self):
        print(f"[SETUP] {self.jid} запущен.")

    class GetBackpackBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=3)
            if msg:
                print(f"Запрос от {msg.sender.jid} для получения рюкзака")
                reply = msg.make_reply()
                reply.set_metadata("type", "weight_reply")
                reply.body = json.dumps(self.agent.backpack)
                await self.send(reply)

    class SaveBackpackBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=3)
            if msg:
                print(f"Запрос от {msg.sender.jid} для сохранения рюкзака")
                new_backpack = json.loads(msg.body)
                self.agent.backpack = new_backpack


class BalanceAgent(Agent):
    def __init__(self, jid, password, hiker_jids):
        super().__init__(jid, password)
        self.balancing_history = []
        self.hiker_jids = hiker_jids

    async def setup(self):
        print(f"[SETUP] {self.jid} запущен.")

    class BalanceBehaviour(PeriodicBehaviour):
        async def run(self):
            curr_backpacks = {}
            for hiker in self.agent.hiker_jids:
                msg = Message(to=hiker)
                msg.set_metadata("type", "weight_request")
                await self.send(msg)
                received_msg = await self.receive(timeout=3)
                if received_msg:
                    backpack = json.loads(received_msg.body)
                    curr_backpacks[hiker] = backpack
                else:
                    print(f"[BALANCER] Не получен ответ от {hiker}")
                    return

            # Вычисляем суммарные веса для каждого агента
            weights = {}
            for jid, backpack in curr_backpacks.items():
                total_weight = sum(item["weight"] for item in backpack)
                weights[jid] = total_weight

            print(f"[BALANCER] Веса до балансировки: {weights}")

            # Проверяем, не было ли такой же конфигурации недавно (предотвращение циклов)
            current_config = tuple(sorted((jid, weight) for jid, weight in weights.items()))
            if current_config in self.agent.balancing_history:
                print(f"[BALANCER] Обнаружена циклическая конфигурация, пропускаем балансировку")
                msg = Message(to="agent_saver@localhost")
                msg.set_metadata("type", "saveallbackpacks_request")
                msg.body = json.dumps(curr_backpacks)
                await self.send(msg)
                await self.agent.stop()
                return

            # Сохраняем текущую конфигурацию (оставляем только последние 10)
            self.agent.balancing_history.append(current_config)
            if len(self.agent.balancing_history) > 10:
                self.agent.balancing_history.pop(0)

            # Находим самого тяжелого и самого легкого
            heaviest_jid = max(weights, key=weights.get)
            lightest_jid = min(weights, key=weights.get)

            # Проверяем нужно ли балансировать
            if heaviest_jid == lightest_jid:
                print("[BALANCER] Веса равны, балансировка не требуется")
                msg = Message(to="agent_saver@localhost")
                msg.set_metadata("type", "saveallbackpacks_request")
                msg.body = json.dumps(curr_backpacks)
                await self.send(msg)
                await self.agent.stop()
                return

            diff = weights[heaviest_jid] - weights[lightest_jid]
            if diff <= 2:  # порог балансировки
                print(f"[BALANCER] Разница {diff}кг слишком мала")
                msg = Message(to="agent_saver@localhost")
                msg.set_metadata("type", "saveallbackpacks_request")
                msg.body = json.dumps(curr_backpacks)
                await self.send(msg)
                await self.agent.stop()
                return

            print(
                f"[BALANCER] Балансируем: {heaviest_jid}({weights[heaviest_jid]}кг) → {lightest_jid}({weights[lightest_jid]}кг)")

            # УЛУЧШЕННЫЙ АЛГОРИТМ ВЫБОРА ПРЕДМЕТА
            heaviest_backpack = curr_backpacks[heaviest_jid]
            if not heaviest_backpack:
                print(f"[BALANCER] У {heaviest_jid} нет предметов")
                return

            # Целевой вес после передачи (стремимся к равенству)
            target_weight_after = (weights[heaviest_jid] + weights[lightest_jid]) / 2

            # Ищем предмет, который приблизит нас к целевому весу
            best_item = None
            best_improvement = float('inf')  # Минимальная разница от целевого веса

            for item in heaviest_backpack:
                # Предполагаемые веса после передачи
                new_heavy_weight = weights[heaviest_jid] - item["weight"]
                new_light_weight = weights[lightest_jid] + item["weight"]

                # Новая разница между самыми тяжелым и легким
                new_max_weight = max(new_heavy_weight, max(w for jid, w in weights.items() if jid != heaviest_jid))
                new_min_weight = min(new_light_weight, min(w for jid, w in weights.items() if jid != lightest_jid))
                new_diff = new_max_weight - new_min_weight

                # Насколько мы приближаемся к идеальному балансу
                improvement = abs(new_heavy_weight - target_weight_after) + abs(new_light_weight - target_weight_after)

                if improvement < best_improvement and new_diff < diff:
                    best_improvement = improvement
                    best_item = item

            # Если не нашли подходящий предмет, берем самый легкий
            if not best_item:
                best_item = min(heaviest_backpack, key=lambda x: x["weight"])
                print(f"[BALANCER] Не найден оптимальный предмет, берем самый легкий")

            print(f"[BALANCER] Передаем: {best_item['name']} ({best_item['weight']}кг)")

            # Обновляем локальные данные
            curr_backpacks[heaviest_jid] = [item for item in curr_backpacks[heaviest_jid] if item != best_item]
            curr_backpacks[lightest_jid] = curr_backpacks[lightest_jid] + [best_item]

            # Вычисляем новые веса
            new_weights = {}
            for jid, backpack in curr_backpacks.items():
                total_weight = sum(item["weight"] for item in backpack)
                new_weights[jid] = total_weight

            print(f"[BALANCER] Веса после балансировки: {new_weights}")

            # Статистика улучшения
            old_std = self.calculate_std_dev(list(weights.values()))
            new_std = self.calculate_std_dev(list(new_weights.values()))
            print(f"[BALANCER] Стандартное отклонение: {old_std:.2f} → {new_std:.2f}")

            # Рассылаем обновления ТОЛЬКО тем, у кого изменился рюкзак
            updated_hikers = [heaviest_jid, lightest_jid]
            for hiker in updated_hikers:
                msg = Message(to=hiker)
                msg.set_metadata("type", "save_request")
                msg.body = json.dumps(curr_backpacks[hiker])
                await self.send(msg)
                print(f"[BALANCER] Отправлено обновление для {hiker}")

            print(f"[BALANCER] Цикл балансировки завершен")
            print(f"{'=' * 50}")

        def calculate_std_dev(self, values):
            """Вычисляет стандартное отклонение для оценки равномерности распределения"""
            if len(values) <= 1:
                return 0
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance ** 0.5


class BackpacksSaverAgent(Agent):
    def __init__(self, jid, password, output_file):
        super().__init__(jid, password)
        self.output_file = output_file

    async def setup(self):
        print(f"[SETUP] {self.jid} запущен.")

    class SaveAllHikerBackpacksBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=3)
            if msg:
                print(f"Запрос от {msg.sender.jid} для сохранения рюкзаков туристов в файл")
                backpacks = json.loads(msg.body)
                self.save_backpacks_to_json(backpacks)

        def save_backpacks_to_json(self, backpacks):
            """Сохраняет текущее состояние рюкзаков в JSON файл"""
            try:
                # Преобразуем данные для сохранения
                save_data = {}
                for jid, backpack in backpacks.items():
                    save_data[jid] = {
                        "backpack": backpack,
                        "total_weight": sum(item["weight"] for item in backpack)
                    }

                with open(self.agent.output_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)

                print(f"[BALANCER] Рюкзаки сохранены в файл: {self.agent.output_file}")
                return True
            except Exception as e:
                print(f"[BALANCER] Ошибка при сохранении в JSON: {e}")
                return False


def load_hikers_from_json(input_file):
    """Загружает данные о туристах из JSON файла"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        hikers = []
        for hiker_data in data.get("hikers", []):
            jid = hiker_data.get("jid")
            backpack = hiker_data.get("backpack", [])
            hikers.append({
                "jid": jid,
                "backpack": backpack
            })

        print(f"Загружено {len(hikers)} туристов из файла {input_file}")
        return hikers
    except Exception as e:
        print(f"Ошибка при загрузке файла {input_file}: {e}")
        return []


async def main(input_file, output_file):
    # Загружаем данные о туристах
    hikers_data = load_hikers_from_json(input_file)
    if not hikers_data:
        print("Не удалось загрузить данные о туристах")
        return

    # Создаем агентов-туристов
    hiker_agents = []
    hiker_jids = []

    for hiker_data in hikers_data:
        hiker = HikerAgent(
            jid=hiker_data["jid"],
            password="pass",
            initial_items=hiker_data["backpack"]
        )
        hiker_agents.append(hiker)
        hiker_jids.append(hiker_data["jid"])

    # Создаем балансировщик и агент для сохранения
    balancer = BalanceAgent("agent_balancer@localhost", "pass", hiker_jids)
    saver = BackpacksSaverAgent("agent_saver@localhost", "pass", output_file)

    # Настраиваем шаблоны для поведения
    weight_template_reply = Template(metadata={"type": "weight_reply"})
    save_all_backpacks_template = Template(metadata={"type": "saveallbackpacks_request"})
    weight_template = Template(metadata={"type": "weight_request"})
    save_backpack_template = Template(metadata={"type": "save_request"})

    # Добавляем поведения
    balancer.add_behaviour(balancer.BalanceBehaviour(10), weight_template_reply)
    saver.add_behaviour(saver.SaveAllHikerBackpacksBehaviour(), save_all_backpacks_template)

    for hiker in hiker_agents:
        hiker.add_behaviour(hiker.GetBackpackBehaviour(), weight_template)
        hiker.add_behaviour(hiker.SaveBackpackBehaviour(), save_backpack_template)

    # Запускаем всех агентов
    for hiker in hiker_agents:
        await hiker.start()

    await balancer.start()
    await saver.start()

    # Ждем завершения работы балансировщика
    while balancer.is_alive():
        await asyncio.sleep(1)

    # Останавливаем всех агентов
    for hiker in hiker_agents:
        await hiker.stop()
    await saver.stop()

    print(f"\nБалансировка завершена. Результат сохранен в: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Система балансировки рюкзаков туристов")
    parser.add_argument("--input", "-i", required=True, help="Путь к входному JSON файлу с данными о туристах")
    parser.add_argument("--output", "-o", required=True, help="Путь к выходному JSON файлу для сохранения результатов")

    args = parser.parse_args()

    # Проверяем существование входного файла
    if not Path(args.input).exists():
        print(f"Ошибка: Входной файл {args.input} не существует")
        exit(1)

    # Запускаем основную программу
    asyncio.run(main(args.input, args.output))