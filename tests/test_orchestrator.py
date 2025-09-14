import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import src.orchestrator as orchestrator_module  # Import the module itself


# --- Tests for extract_json_from_hermes_output ---
@pytest.mark.success
def test_extract_json_from_hermes_output_with_fences():
    hermes_output = """
    Some text before.
    ```json
    {"thought": "hello", "tool_calls": []}
    ```
    Some text after.
    """
    result = orchestrator_module.extract_json_from_hermes_output(hermes_output)
    assert result == {"thought": "hello", "tool_calls": []}


@pytest.mark.success
def test_extract_json_from_hermes_output_without_fences():
    hermes_output = '{"thought": "hello", "tool_calls": []}'
    result = orchestrator_module.extract_json_from_hermes_output(hermes_output)
    assert result == {"thought": "hello", "tool_calls": []}


@pytest.mark.error
def test_extract_json_from_hermes_output_invalid_json():
    hermes_output = "this is not json"
    with pytest.raises(orchestrator_module.JsonExtractionError):
        orchestrator_module.extract_json_from_hermes_output(hermes_output)


@pytest.mark.error
def test_extract_json_from_hermes_output_malformed_json_in_fences():
    hermes_output = """
    ```json
    {"thought": "hello", "tool_calls": [}
    ```
    """
    with pytest.raises(orchestrator_module.JsonExtractionError):
        orchestrator_module.extract_json_from_hermes_output(hermes_output)


@pytest.mark.edge_case
def test_extract_json_from_hermes_output_empty_fenced_json():
    hermes_output = """
    ```json

    ```
    """
    with pytest.raises(orchestrator_module.JsonExtractionError):
        orchestrator_module.extract_json_from_hermes_output(hermes_output)


# --- Mocks for httpx client ---
@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as MockAsyncClientClass:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        MockAsyncClientClass.return_value = mock_client_instance

        mock_response_get = AsyncMock()
        mock_response_post = AsyncMock()

        mock_response_get.text = AsyncMock()
        mock_response_post.text = AsyncMock()

        mock_response_get.raise_for_status = MagicMock()
        mock_response_post.raise_for_status = MagicMock()

        mock_client_instance.get.return_value = mock_response_get
        mock_client_instance.post.return_value = mock_response_post

        yield mock_client_instance


# --- Tests for execute_tool_call ---
@pytest.mark.success
@pytest.mark.asyncio
async def test_execute_tool_call_list_files_success(mock_httpx_client):
    mock_httpx_client.get.return_value.status_code = 200
    mock_httpx_client.get.return_value.text = json.dumps({"files": ["a.txt"]})  # 変更
    mock_httpx_client.get.return_value.raise_for_status.return_value = None

    tool_call = {"tool_name": "list_files", "args": {"extensions": ".txt"}}
    trace_id = "test-trace-id"
    result = await orchestrator_module.execute_tool_call(tool_call, trace_id)

    mock_httpx_client.get.assert_called_once_with(
        "/list_files", params={"extensions": ".txt"}, headers={"X-Trace-ID": trace_id}
    )
    assert result == {"files": ["a.txt"]}


@pytest.mark.success
@pytest.mark.asyncio
async def test_execute_tool_call_read_file_success(mock_httpx_client):
    mock_httpx_client.get.return_value.status_code = 200
    mock_httpx_client.get.return_value.text = json.dumps(
        {"content": "file content"}
    )  # 変更
    mock_httpx_client.get.return_value.raise_for_status.return_value = None

    tool_call = {"tool_name": "read_file", "args": {"file_path": "test.txt"}}
    trace_id = "test-trace-id"
    result = await orchestrator_module.execute_tool_call(tool_call, trace_id)

    mock_httpx_client.get.assert_called_once_with(
        "/read_file", params={"file_path": "test.txt"}, headers={"X-Trace-ID": trace_id}
    )
    assert result == {"content": "file content"}


@pytest.mark.success
@pytest.mark.asyncio
async def test_execute_tool_call_write_file_success(mock_httpx_client):
    mock_httpx_client.post.return_value.status_code = 200
    # mock_httpx_client.post.return_value.json.return_value = {}  # 削除
    mock_httpx_client.post.return_value.raise_for_status.return_value = None

    tool_call = {
        "tool_name": "write_file",
        "args": {"file_path": "test.txt", "content": "new content"},
    }
    trace_id = "test-trace-id"
    result = await orchestrator_module.execute_tool_call(tool_call, trace_id)

    mock_httpx_client.post.assert_called_once_with(
        "/write_file?file_path=test.txt",
        json={"content": "new content"},
        headers={"X-Trace-ID": trace_id},
    )
    assert result == {}  # Corrected assertion


@pytest.mark.error
@pytest.mark.asyncio
async def test_execute_tool_call_write_file_missing_args(mock_httpx_client):
    tool_call = {
        "tool_name": "write_file",
        "args": {"file_path": "test.txt"},  # Missing 'content'
    }
    trace_id = "test-trace-id"
    with pytest.raises(KeyError):
        await orchestrator_module.execute_tool_call(tool_call, trace_id)


@pytest.mark.error
@pytest.mark.asyncio
async def test_execute_tool_call_unsupported_tool(mock_httpx_client):
    tool_call = {"tool_name": "unsupported_tool", "args": {}}
    trace_id = "test-trace-id"
    with pytest.raises(
        orchestrator_module.PolicyError, match="Unsupported tool: unsupported_tool"
    ):
        await orchestrator_module.execute_tool_call(tool_call, trace_id)


@pytest.mark.error
@pytest.mark.asyncio
async def test_execute_tool_call_mcp_http_error(mock_httpx_client):
    mock_response = AsyncMock(spec=httpx.Response)  # spec を追加
    mock_response.status_code = 400
    mock_response.text = "{}"  # 変更

    mock_httpx_client.get.side_effect = httpx.HTTPStatusError(
        "Client error", request=httpx.Request("GET", "/"), response=mock_response
    )

    tool_call = {"tool_name": "list_files", "args": {}}
    trace_id = "test-trace-id"
    with pytest.raises(
        orchestrator_module.ExecutionError,
        match="MCP returned error: 400 - {}",
    ):
        await orchestrator_module.execute_tool_call(tool_call, trace_id)


@pytest.mark.error
@pytest.mark.asyncio
async def test_execute_tool_call_mcp_connection_error(mock_httpx_client):
    # No need to mock raise_for_status here, as RequestError is caught earlier
    mock_httpx_client.get.side_effect = httpx.RequestError(
        "Connection refused", request=httpx.Request("GET", "/")
    )

    tool_call = {"tool_name": "list_files", "args": {}}
    trace_id = "test-trace-id"
    with pytest.raises(
        orchestrator_module.ExecutionError,
        match="Failed to connect to MCP: Connection refused",
    ):
        await orchestrator_module.execute_tool_call(tool_call, trace_id)


# --- Tests for orchestrate ---
@pytest.mark.success
@pytest.mark.asyncio
async def test_orchestrate_success(mock_httpx_client):
    mock_httpx_client.post.return_value.status_code = 200
    # mock_httpx_client.post.return_value.json.return_value = {}  # 削除
    mock_httpx_client.post.return_value.raise_for_status.return_value = None
    mock_httpx_client.get.return_value.status_code = 200
    mock_httpx_client.get.return_value.text = json.dumps(
        {"content": "read content"}
    )  # 変更
    mock_httpx_client.get.return_value.raise_for_status.return_value = None

    hermes_output = """
    ```json
    {
      "thought": "Executing two tools.",
      "tool_calls": [
        {"tool_name": "write_file", "args": {"file_path": "test.txt", "content": "hello"}},
        {"tool_name": "read_file", "args": {"file_path": "test.txt"}}
      ],
      "final_answer": "Done."
    }
    ```
    """
    exit_code = await orchestrator_module.orchestrate(hermes_output)
    assert exit_code == 0
    assert mock_httpx_client.post.call_count == 1
    assert mock_httpx_client.get.call_count == 1


@pytest.mark.error
@pytest.mark.asyncio
async def test_orchestrate_json_extraction_error():
    hermes_output = "invalid json"
    exit_code = await orchestrator_module.orchestrate(hermes_output)
    assert exit_code == 3


@pytest.mark.error
@pytest.mark.asyncio
async def test_orchestrate_policy_error(mock_httpx_client):
    hermes_output = """
    ```json
    {
      "thought": "Executing unsupported tool.",
      "tool_calls": [
        {"tool_name": "unsupported_tool", "args": {}}
      ],
      "final_answer": "Done."
    }
    ```
    """
    exit_code = await orchestrator_module.orchestrate(hermes_output)
    assert exit_code == 2


@pytest.mark.error
@pytest.mark.asyncio
async def test_orchestrate_execution_error(mock_httpx_client):
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    # raise_for_status を同期モックとして設定
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Client error", request=httpx.Request("GET", "/"), response=mock_response
        )
    )
    mock_httpx_client.get.return_value = mock_response  # Assign the mock response

    hermes_output = """
    ```json
    {
      "thought": "Executing tool that fails.",
      "tool_calls": [
        {"tool_name": "read_file", "args": {"file_path": "non_existent.txt"}}
      ],
      "final_answer": "Done."
    }
    ```
    """
    exit_code = await orchestrator_module.orchestrate(hermes_output)
    assert exit_code == 1
