import argparse
import asyncio
import sys
from pathlib import Path

from .orchestrator import orchestrate


async def main():
    parser = argparse.ArgumentParser(
        description="Orchestrates tool calls based on Hermes output."
    )
    parser.add_argument(
        "--hermes-output",
        required=True,
        help="JSON output from Hermes (can be a string or a file path).",
    )

    args = parser.parse_args()

    hermes_output_content = args.hermes_output
    # Check if the input is a file path
    if Path(
        hermes_output_content
    ).is_file():  # Removed .endswith(".json") check for flexibility
        with open(hermes_output_content, encoding="utf-8") as f:
            hermes_output_content = f.read()

    exit_code = await orchestrate(hermes_output_content)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
