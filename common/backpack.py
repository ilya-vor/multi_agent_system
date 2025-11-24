import json
import os
from common.get_time import get_time


def load_plan_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("tasks", [])
    except Exception as e:
        print(f"Ошибка загрузки {file_path}: {e}")
        return []


def save_plan_to_file(old_file_path, plan):
    directory = os.path.dirname(old_file_path)
    parent_dir = os.path.dirname(directory)
    new_file_path = os.path.join(parent_dir, "new", os.path.basename(old_file_path))
    try:
        data = {
            "plan": plan,
            "total_weight": sum(item["time"] for item in plan)
        }
        with open(new_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{get_time()} [SAVE] План сохранен в {new_file_path}, вес: {data['total_weight']}")
        return True
    except Exception as e:
        print(f"{get_time()} [SAVE] Ошибка сохранения {new_file_path}: {e}")
        return False