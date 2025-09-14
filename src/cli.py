import argparse
import asyncio
import sys

from .orchestrator import orchestrate


async def main():
    parser = argparse.ArgumentParser(
        description="Orchestrates tool calls based on Hermes output."
    )
    parser.add_argument(
        "--hermes-output",
        help="JSON output from Hermes (as a string).",
    )
    parser.add_argument(
        "--hermes-output-file",
        help="Path to a file containing JSON output from Hermes.",
    )

    args = parser.parse_args()

    hermes_output_content = None
    if args.hermes_output_file:
        with open(args.hermes_output_file, encoding="utf-8") as f:
            hermes_output_content = f.read()
    elif args.hermes_output:
        hermes_output_content = args.hermes_output
    else:
        parser.error("Either --hermes-output or --hermes-output-file must be provided.")

    # The existing Path().is_file() check is no longer needed as we explicitly handle file input
    # if Path(hermes_output_content).is_file():
    #     with open(hermes_output_content, encoding="utf-8") as f:
    #         hermes_output_content = f.read()

    exit_code = await orchestrate(hermes_output_content)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
