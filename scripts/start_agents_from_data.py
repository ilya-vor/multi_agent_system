"""
Start agents from `common/agents.json`. Default is dry-run (does not import spade).
Usage examples:
  - Dry-run (default): prints summary and suggested single-agent commands
      python .\scripts\start_agents_from_data.py

  - Dry-run with explicit files:
      python .\scripts\start_agents_from_data.py --agents-file common/agents.json --tasks-file common/tasks.json

  - Start a single agent (attempts to import spade; will fail if not installed):
      python .\scripts\start_agents_from_data.py --start-jid worker1@26.3.185.180

Note: for real runs you need `spade` installed and reachable XMPP accounts.
"""
import argparse
import json
from pathlib import Path


def load_json(p: Path):
    with p.open(encoding='utf-8') as f:
        return json.load(f)


def build_parser():
    p = argparse.ArgumentParser(description='Start agents from data files')
    p.add_argument('--agents-file', default='common/agents.json', help='Path to agents.json')
    p.add_argument('--tasks-file', default='common/tasks.json', help='Path to tasks.json')
    p.add_argument('--dry-run', action='store_true', default=True, help='Only print commands and summaries')
    p.add_argument('--start-jid', help='Start only this agent (use with spade installed)')
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    agents_path = Path(args.agents_file)
    tasks_path = Path(args.tasks_file)

    if not agents_path.exists():
        print(f'Agents file not found: {agents_path}')
        return

    agents = load_json(agents_path)
    tasks = load_json(tasks_path) if tasks_path.exists() else []

    print(f"Loaded {len(agents)} agents from {agents_path}")
    print(f"Loaded {len(tasks)} tasks from {tasks_path if tasks_path.exists() else 'none'}")

    for a in agents:
        print('\n---')
        print(f"JID: {a.get('jid')}")
        print(f"Backpack file: {a.get('backpack_file')}")
        print(f"Specialization: {a.get('specialization')}")
        print(f"Other workers: {a.get('other_workers')}")
        # Suggested command to run single agent
        cmd = f"python .\\common\\main.py --jid {a.get('jid')} --password {a.get('password')} --backpack-file {a.get('backpack_file')} --other_workers {' '.join(a.get('other_workers', []))} --specialization {a.get('specialization')}"
        print('Suggested single-agent command:')
        print(cmd)

    # If user requested to start a specific agent, try to import spade and start
    if args.start_jid:
        print(f"\nAttempting to start agent {args.start_jid} (requires spade)...")
        try:
            from agent.agent import WorkerAgent
        except Exception as e:
            print('Could not import WorkerAgent (spade missing or import error):', e)
            return

        # find agent in list
        target = next((x for x in agents if x.get('jid') == args.start_jid), None)
        if not target:
            print('Agent JID not found in agents file')
            return

        import asyncio

        async def run_one():
            backpack_file = target.get('backpack_file')
            worker = WorkerAgent(
                jid=target.get('jid'),
                password=target.get('password'),
                backpack_file=backpack_file,
                initial_items=None,
                other_workers=target.get('other_workers', []),
                specialization=target.get('specialization')
            )
            await worker.start()
            print('Agent started; press Ctrl+C to stop')
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print('Stopping...')
                await worker.stop()

        asyncio.run(run_one())


if __name__ == '__main__':
    main()
