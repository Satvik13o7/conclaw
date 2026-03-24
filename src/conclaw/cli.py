from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from conclaw.agent import decide
from conclaw.config import AppConfig
from conclaw.db import init_db
from conclaw.fs_ops import read_file, write_file
from conclaw.memory import get_memory, list_memory, upsert_memory
from conclaw.safety import SafetyLayer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="conclaw")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("--db-mode", default="system_or_docker")
    init_p.add_argument("--dsn", default="postgresql://conclaw:conclaw@localhost:5433/conclaw")
    init_p.add_argument("--model", default="gpt-5.0")
    init_p.add_argument(
        "--filesystem-permission",
        choices=["full_access", "prompt_session", "prompt_sensitive"],
        default="full_access",
    )

    db_p = sub.add_parser("db")
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("up")
    db_sub.add_parser("init")

    mem_p = sub.add_parser("memory")
    mem_sub = mem_p.add_subparsers(dest="memory_command", required=True)
    m_set = mem_sub.add_parser("set")
    m_set.add_argument("--scope", default="global")
    m_set.add_argument("--key", required=True)
    m_set.add_argument("--value", required=True)

    m_get = mem_sub.add_parser("get")
    m_get.add_argument("--scope", default="global")
    m_get.add_argument("--key", required=True)

    m_list = mem_sub.add_parser("list")
    m_list.add_argument("--scope", default="global")
    m_list.add_argument("--limit", type=int, default=20)

    dec_p = sub.add_parser("decide")
    dec_p.add_argument("--scope", default="global")
    dec_p.add_argument("--task", required=True)

    fs_p = sub.add_parser("fs")
    fs_sub = fs_p.add_subparsers(dest="fs_command", required=True)
    fs_read = fs_sub.add_parser("read")
    fs_read.add_argument("--path", required=True)

    fs_write = fs_sub.add_parser("write")
    fs_write.add_argument("--path", required=True)
    fs_write.add_argument("--content", required=True)

    return parser


def _run_docker_up() -> None:
    compose_file = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        cfg = AppConfig(
            db_mode=args.db_mode,
            dsn=args.dsn,
            model_name=args.model,
            filesystem_permission=args.filesystem_permission,
            safety_layer="baseline",
        )
        cfg.save()
        print(
            "Conclaw initialized "
            f"(db_mode={cfg.db_mode}, model={cfg.model_name}, fs={cfg.filesystem_permission})."
        )
        return

    cfg = AppConfig.load()
    safety = SafetyLayer(permission_mode=cfg.filesystem_permission)

    if args.command == "db":
        if args.db_command == "up":
            _run_docker_up()
            print("Local PostgreSQL started with Docker on port 5433.")
            return
        if args.db_command == "init":
            init_db(cfg)
            print("Database schema initialized.")
            return

    if args.command == "memory":
        if args.memory_command == "set":
            upsert_memory(cfg, scope=args.scope, key=args.key, value=args.value)
            print("Memory updated.")
            return
        if args.memory_command == "get":
            value = get_memory(cfg, scope=args.scope, key=args.key)
            print(value if value is not None else "(not found)")
            return
        if args.memory_command == "list":
            rows = list_memory(cfg, scope=args.scope, limit=args.limit)
            for key, value in rows:
                print(f"{key}={value}")
            return

    if args.command == "decide":
        decision = decide(cfg, scope=args.scope, task=args.task)
        print(decision)
        return

    if args.command == "fs":
        if args.fs_command == "read":
            print(read_file(args.path, safety))
            return
        if args.fs_command == "write":
            write_file(args.path, args.content, safety)
            print("File written.")
            return


if __name__ == "__main__":
    main()
