"""Hermes CLI for nvk/llm-wiki plugin management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from runtime import (
    activate_plugin,
    get_status,
    load_upstream_metadata,
    run_doctor,
    sync_managed_skill_bundle,
    ALL_COMMANDS,
)


_WIKI_PARSER: argparse.ArgumentParser | None = None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    global _WIKI_PARSER

    parser = argparse.ArgumentParser(
        prog="nvk-llm-wiki",
        description="Hermes adapter for nvk/llm-wiki",
    )
    sub = parser.add_subparsers(dest="command")

    sp = sub.add_parser("sync", help="Sync managed skill bundle from vendor")
    sp.add_argument("--vendor", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--lock", default=None)

    dp = sub.add_parser("doctor", help="Run integrity checks")
    dp.add_argument("--lock", required=True)
    dp.add_argument("--vendor", required=True)
    dp.add_argument("--skill-root", required=True)
    dp.add_argument("--config", required=True)
    dp.add_argument("--fix", action="store_true", help="Auto-fix by resyncing")

    sp2 = sub.add_parser("status", help="Show plugin status")
    sp2.add_argument("--lock", required=True)
    sp2.add_argument("--skill-root", required=True)
    sp2.add_argument("--config", required=True)

    ap = sub.add_parser("activate", help="Activate plugin in Hermes config")
    ap.add_argument("--config", required=True)
    ap.add_argument("--managed-root", required=True)

    wp = sub.add_parser("wiki", help="Route to a wiki command alias")
    wp.add_argument("wiki_action", nargs="?", choices=sorted(ALL_COMMANDS))
    wp.add_argument("wiki_args", nargs=argparse.REMAINDER)
    _WIKI_PARSER = wp

    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entrypoint. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    match args.command:
        case "sync":
            meta = None
            if args.lock:
                meta = load_upstream_metadata(args.lock)
            result = sync_managed_skill_bundle(
                vendor_dir=args.vendor,
                output_dir=args.output,
                meta=meta,
            )
            print(json.dumps(result, indent=2))
            return 0

        case "doctor":
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            if args.fix:
                meta = (
                    load_upstream_metadata(args.lock)
                    if Path(args.lock).exists()
                    else None
                )
                sync_managed_skill_bundle(
                    vendor_dir=args.vendor,
                    output_dir=str(Path(args.skill_root).parent.parent),
                    meta=meta,
                )
                print("Resynced")
                return 0
            result = run_doctor(
                lock_path=args.lock,
                vendor_dir=args.vendor,
                skill_root=args.skill_root,
                config=config,
            )
            print(json.dumps(result, indent=2))
            return 0 if result["healthy"] else 1

        case "status":
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            result = get_status(
                lock_path=args.lock,
                skill_root=args.skill_root,
                config=config,
            )
            print(json.dumps(result, indent=2))
            return 0

        case "activate":
            result = activate_plugin(
                config_path=args.config,
                managed_root=args.managed_root,
            )
            print(json.dumps(result, indent=2))
            return 0

        case "wiki":
            action = getattr(args, "wiki_action", None)
            if action:
                suffix = f" with args: {args.wiki_args}" if args.wiki_args else ""
                print(f"Routing to wiki-{action}{suffix}")
                return 0
            _WIKI_PARSER.print_help()
            return 1

        case _:
            parser.print_help()
            return 1


def register_cli(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    """Set up the CLI argument parser (Hermes setup_fn contract).

    Uses the existing build_parser internally. Accepts an optional parser
    to maintain Hermes compatibility.
    """
    return build_parser()


def wiki_command(args: argparse.Namespace) -> int:
    """Handle a wiki CLI invocation (Hermes handler_fn contract).

    Delegates to main() with the subcommand routed appropriately.
    """
    return main([args.command] if hasattr(args, "command") and args.command else [])


if __name__ == "__main__":
    sys.exit(main())
