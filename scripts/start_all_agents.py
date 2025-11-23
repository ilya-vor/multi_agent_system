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
    p.add_argument("--agents-file", default="common/agents.json", help="Path to agents.json")
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
