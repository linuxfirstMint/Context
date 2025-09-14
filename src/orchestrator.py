import json
import uuid
from typing import Any

import httpx

MCP_BASE_URL = "http://localhost:8000"


class OrchestratorError(Exception):
    """Base exception for Orchestrator errors."""

    pass


class JsonExtractionError(OrchestratorError):
    """Raised when JSON extraction fails."""

    pass


class PolicyError(OrchestratorError):
    """Raised when a policy is violated."""

    pass


class ExecutionError(OrchestratorError):
    """Raised when a tool execution fails."""

    pass


def extract_json_from_hermes_output(output: str) -> dict[str, Any]:
    """
    Extracts JSON from Hermes output, handling JSON fences and retrying once.
    """
    # Attempt to find JSON within fences
    try:
        start_idx = output.find("```json")
        end_idx = output.find("```", start_idx + 1)
        if start_idx != -1 and end_idx != -1:
            json_str = output[start_idx + len("```json") : end_idx].strip()
            return json.loads(json_str)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass  # Will retry

    # If not found in fences or decode failed, try to parse the whole output
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        raise JsonExtractionError(f"Failed to extract valid JSON: {e}")


async def execute_tool_call(tool_call: dict[str, Any], trace_id: str) -> Any:
    """
    Executes a single tool call against the MCP.
    """
    headers = {"X-Trace-ID": trace_id}

    tool_name = tool_call.get("tool_name")
    args = tool_call.get("args", {})  # Define here

    try:
        async with httpx.AsyncClient(base_url=MCP_BASE_URL) as client:  # Use async with
            if tool_name == "list_files":
                response = await client.get("/list_files", params=args, headers=headers)
            elif tool_name == "read_file":
                response = await client.get("/read_file", params=args, headers=headers)
            elif tool_name == "write_file":
                # For write_file, content is in the body
                file_path = args.pop("file_path")
                content = args.pop("content")
                response = await client.post(
                    f"/write_file?file_path={file_path}",
                    json={"content": content},
                    headers=headers,
                )
            else:
                raise PolicyError(f"Unsupported tool: {tool_name}")

            await response.raise_for_status()
            return await response.json()  # Await the json() method
    except httpx.HTTPStatusError as e:
        raise ExecutionError(
            f"MCP returned error: {e.response.status_code} - {e.response.text}"
        )
    except httpx.RequestError as e:
        raise ExecutionError(f"Failed to connect to MCP: {e}")


async def orchestrate(hermes_output: str) -> int:
    """
    Orchestrates tool calls based on Hermes output.
    Returns exit code: 0 for success, 1 for exec_fail, 2 for policy, 3 for json.
    """
    trace_id = str(uuid.uuid4())
    try:
        hermes_json = extract_json_from_hermes_output(hermes_output)
        tool_calls = hermes_json.get("tool_calls", [])

        for tool_call in tool_calls:
            await execute_tool_call(tool_call, trace_id)

        return 0  # Success
    except JsonExtractionError:
        return 3
    except PolicyError:
        return 2
    except ExecutionError:
        return 1
    except Exception:
        return 1  # Generic execution failure


if __name__ == "__main__":
    # Example usage (for testing)
    # This part will be replaced by CLI integration later
    async def main():
        hermes_sample_output = """
        ```json
        {
          "thought": "I need to write a test file.",
          "tool_calls": [
            {
              "tool_name": "write_file",
              "args": {
                "file_path": "orchestrator_test.txt",
                "content": "Hello from Orchestrator test!"
              }
            },
            {
              "tool_name": "read_file",
              "args": {
                "file_path": "orchestrator_test.txt"
              }
            }
          ],
          "final_answer": "Successfully executed tool calls."
        }
        ```
        """
        exit_code = await orchestrate(hermes_sample_output)
        print(f"Orchestrator finished with exit code: {exit_code}")

    import asyncio

    asyncio.run(main())
