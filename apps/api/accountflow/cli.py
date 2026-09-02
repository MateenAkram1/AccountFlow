import argparse
import asyncio
import json
import sys
from pathlib import Path

from accountflow.core.config import ROOT_DIR
from accountflow.core.logging import setup_logging
from accountflow.models.schemas import Transcript
from accountflow.providers.registry import clear_provider_cache
from accountflow.services.pipeline import (
    DraftEngine,
    HallucinationGrader,
    ScopeVerifier,
    load_account_from_file,
    load_scope_from_file,
)


async def run_pipeline(
    transcript_path: Path,
    account_path: Path,
    sow_path: Path | None,
    llm_provider: str | None,
) -> None:
    import os

    if llm_provider:
        os.environ["LLM_PROVIDER"] = llm_provider
    clear_provider_cache()

    transcript = transcript_path.read_text(encoding="utf-8")
    account = load_account_from_file(account_path)
    scope = load_scope_from_file(sow_path) if sow_path else None

    verifier = ScopeVerifier()
    drafter = DraftEngine()
    grader = HallucinationGrader()

    scope_report = await verifier.verify(transcript, scope)
    package = await drafter.draft(transcript, account, scope_report)
    grades = grader.grade(transcript, package)

    output = {
        "summary": package.summary,
        "scope_report": scope_report.model_dump(),
        "action_package": package.model_dump(),
        "grades": grades,
    }
    print(json.dumps(output, indent=2, default=str))


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="AccountFlow OS CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run pipeline on sample files")
    run_parser.add_argument("--transcript", type=Path, required=True)
    run_parser.add_argument("--account", type=Path, required=True)
    run_parser.add_argument("--sow", type=Path, default=None)
    run_parser.add_argument("--llm", type=str, default=None, help="gemini|ollama_cloud|mock")

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(
            run_pipeline(args.transcript, args.account, args.sow, args.llm)
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
