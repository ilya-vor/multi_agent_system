import sys
import argparse
import json
import asyncio
from pathlib import Path

# Ensure repo root on sys.path so imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agent.agent import WorkerAgent
from common.get_time import get_time


def load_json(p: Path):
    with p.open(encoding='utf-8') as f:
        return json.load(f)


def distribute_tasks(agents_data, tasks):
    # Prepare per-agent backpacks and current total weights
    agent_map = {}
    for a in agents_data:
        agent_map[a['jid']] = {
            'data': a,
            'backpack': [],
            'weight': 0.0
        }

    # For each task, try to assign to an agent whose specialization is allowed
    for t in tasks:
        candidates = []
        allowed = t.get('allowed_professions')
        if allowed:
            for jid, info in agent_map.items():
                spec = info['data'].get('specialization')
                if spec and spec in allowed:
                    candidates.append((jid, info['weight']))
        # if no specialization match, all agents are candidates
        if not candidates:
            candidates = [(jid, info['weight']) for jid, info in agent_map.items()]

        # choose candidate with smallest current weight
        candidates.sort(key=lambda x: x[1])
        chosen_jid = candidates[0][0]

        agent_map[chosen_jid]['backpack'].append(t)
        agent_map[chosen_jid]['weight'] += t.get('weight', 0)

    # Return list of agent definitions with assigned backpacks
    result = []
    for jid, info in agent_map.items():
        ad = info['data'].copy()
        ad['initial_backpack'] = info['backpack']
        result.append(ad)
    return result


async def main():
    parser = argparse.ArgumentParser(description='Start all agents from data files and distribute tasks')
    parser.add_argument('--agents-file', default='common/agents.json')
    parser.add_argument('--tasks-file', default='common/tasks.json')
    parser.add_argument('--dry-run', action='store_true', help='Only show distribution and suggested commands')
    args = parser.parse_args()

    agents_path = Path(args.agents_file)
    tasks_path = Path(args.tasks_file)

    if not agents_path.exists():
        print(f'Agents file not found: {agents_path}')
        return
    if not tasks_path.exists():
        print(f'Tasks file not found: {tasks_path}')
        return

    agents = load_json(agents_path)
    tasks = load_json(tasks_path)

    distributed = distribute_tasks(agents, tasks)

    print(f"{get_time()} Loaded {len(agents)} agents and {len(tasks)} tasks")
    for a in distributed:
        print('---')
        print(f"JID: {a.get('jid')}")
        print(f"Assigned tasks: {len(a.get('initial_backpack', []))}")
        for t in a.get('initial_backpack', []):
            print(f"  - {t.get('id')}: {t.get('name')} ({t.get('weight')})")
        cmd = f"python .\\common\\main.py --jid {a.get('jid')} --password {a.get('password')} --backpack-file {a.get('backpack_file')} --other_workers {' '.join(a.get('other_workers', []))} --specialization {a.get('specialization')}"
        print('Suggested single-agent command:')
        print(cmd)

    if args.dry_run:
        return

    # Instantiate and start all agents
    workers = []
    for a in distributed:
        initial = a.get('initial_backpack', [])
        other_workers = a.get('other_workers', [])
        w = WorkerAgent(
            jid=a.get('jid'),
            password=a.get('password'),
            backpack_file=a.get('backpack_file'),
            initial_items=initial,
            other_workers=other_workers,
            specialization=a.get('specialization')
        )
        workers.append(w)

    try:
        # start all
        for w in workers:
            await w.start()
            print(f"{get_time()} Started {w.jid}")

        print('All agents started; press Ctrl+C to stop')
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print('Stopping agents...')
        for w in workers:
            await w.stop()


if __name__ == '__main__':
    asyncio.run(main())
"""
Start all agents defined in `common/agents.json` concurrently.

Usage:
  - Dry run (default): prints commands and summary
      python .\scripts\start_all_agents.py

  - Start all agents (requires `spade` and valid XMPP accounts):
      python .\scripts\start_all_agents.py --start

Notes:
  - The script inserts the repository root into `sys.path` to allow local imports.
  - If `spade` is not installed, the script will print a helpful error and exit.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Put repo root on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_parser():
    p = argparse.ArgumentParser(description="Start all agents from agents.json")
    p.add_argument("--agents-file", default="../common/agents.json", help="Path to agents.json")
    p.add_argument("--dry-run", action="store_true", default=True, help="Only print commands and summaries (default)")
    p.add_argument("--start", action="store_true", help="Actually start all agents (requires spade and working JIDs)")
    return p


async def run_all(agents_specs):
    # Import here so the script can run dry-run without spade installed
    try:
        from agent.agent import WorkerAgent
        from common.backpack import load_backpack_from_file
    except Exception as e:
        print("Could not import runtime dependencies (spade or local modules).", e)
        raise

    workers = []
    try:
        # create and start agents sequentially (safer); they will run concurrently inside spade
        for spec in agents_specs:
            jid = spec.get("jid")
            password = spec.get("password")
            backpack_file = spec.get("backpack_file")
            other_workers = spec.get("other_workers", [])
            specialization = spec.get("specialization")

            initial_items = None
            if backpack_file:
                try:
                    initial_items = load_backpack_from_file(backpack_file)
                except Exception:
                    initial_items = None

            print(f"Starting {jid} (specialization={specialization})...")
            worker = WorkerAgent(
                jid=jid,
                password=password,
                backpack_file=backpack_file,
                initial_items=initial_items,
                other_workers=other_workers,
                specialization=specialization,
            )
            await worker.start()
            print(f"Started {jid}")
            workers.append(worker)

        print("All agents started. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping agents...")

    finally:
        for w in workers:
            try:
                await w.stop()
                print(f"Stopped {w.jid}")
            except Exception:
                pass


def main():
    parser = build_parser()
    args = parser.parse_args()

    agents_path = Path(args.agents_file)
    if not agents_path.exists():
        print(f"Agents file not found: {agents_path}")
        return

    agents = load_json(agents_path)
    print(f"Loaded {len(agents)} agents from {agents_path}")

    for a in agents:
        print('---')
        print(f"JID: {a.get('jid')}")
        print(f"Backpack file: {a.get('backpack_file')}")
        print(f"Specialization: {a.get('specialization')}")
        print(f"Other workers: {a.get('other_workers')}")
        cmd = f"python .\\common\\main.py --jid {a.get('jid')} --password {a.get('password')} --backpack-file {a.get('backpack_file')} --other_workers {' '.join(a.get('other_workers', []))} --specialization {a.get('specialization')}"
        print('Suggested single-agent command:')
        print(cmd)

    if args.start:
        try:
            asyncio.run(run_all(agents))
        except Exception as e:
            print('Failed to start agents:', e)


if __name__ == '__main__':
    main()
