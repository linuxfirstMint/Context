import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import (  # Import BASE_DIR and MAX_FILE_SIZE_BYTES
    BASE_DIR,
    MAX_FILE_SIZE_BYTES,
    app,
)


@pytest.fixture(scope="function")
def tmp_app_data_dir(tmp_path):  # Use pytest's tmp_path fixture
    """Fixture to create a temporary app_data directory for tests."""
    original_base_dir = BASE_DIR
    temp_dir = (
        tmp_path / "test_app_data"
    )  # Use tmp_path for absolute temporary directory
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Temporarily change BASE_DIR in src.main for tests
    import src.main

    src.main.BASE_DIR = temp_dir  # Set to absolute temporary path

    yield temp_dir

    # Clean up after the test
    shutil.rmtree(temp_dir, ignore_errors=True)
    src.main.BASE_DIR = original_base_dir


client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_list_files_empty(tmp_app_data_dir):
    response = client.get("/list_files")
    assert response.status_code == 200
    assert response.json() == {"files": []}


def test_write_and_read_file_success(tmp_app_data_dir):
    file_path = "test_dir/test_file.txt"
    file_content = "Hello, FastAPI!"
    response = client.post(
        f"/write_file?file_path={file_path}", json={"content": file_content}
    )
    assert response.status_code == 200

    response = client.get(f"/read_file?file_path={file_path}")
    assert response.status_code == 200
    assert response.json() == {"content": file_content}


def test_list_files_with_content(tmp_app_data_dir):
    (tmp_app_data_dir / "file1.txt").write_text("content1")
    (tmp_app_data_dir / "subdir").mkdir(
        parents=True, exist_ok=True
    )  # Create subdir as directory
    (tmp_app_data_dir / "subdir/file2.log").write_text(
        "content2"
    )  # Write file inside subdir
    (tmp_app_data_dir / "file3.md").write_text("content3")

    response = client.get("/list_files")
    assert response.status_code == 200
    files = response.json()["files"]
    assert "file1.txt" in files
    assert "subdir/file2.log" in files
    assert "file3.md" in files
    assert len(files) == 3


def test_list_files_filter_extensions(tmp_app_data_dir):
    (tmp_app_data_dir / "file1.txt").write_text("content1")
    (tmp_app_data_dir / "file2.log").write_text("content2")
    (tmp_app_data_dir / "file3.md").write_text("content3")

    response = client.get("/list_files?extensions=.txt,.md")
    assert response.status_code == 200
    files = response.json()["files"]
    assert "file1.txt" in files
    assert "file3.md" in files
    assert "file2.log" not in files
    assert len(files) == 2


def test_list_files_max_items(tmp_app_data_dir):
    for i in range(5):
        (tmp_app_data_dir / f"file{i}.txt").write_text(f"content{i}")

    response = client.get("/list_files?max_items=2")
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 2


def test_read_file_not_found(tmp_app_data_dir):
    response = client.get("/read_file?file_path=non_existent.txt")
    assert response.status_code == 404


def test_read_file_path_traversal(tmp_app_data_dir):
    # Create a dummy file outside the allowed BASE_DIR to simulate traversal target
    (Path(__file__).parent / "outside.txt").write_text("secret")
    response = client.get("/read_file?file_path=../outside.txt")
    assert response.status_code == 400
    assert "Path traversal detected" in response.json()["detail"]
    (Path(__file__).parent / "outside.txt").unlink()  # Clean up


def test_read_file_invalid_extension(tmp_app_data_dir):
    (tmp_app_data_dir / "image.jpg").write_bytes(b"dummy_image_data")
    response = client.get("/read_file?file_path=image.jpg")
    assert response.status_code == 400
    assert "Extension .jpg not allowed" in response.json()["detail"]


def test_write_file_path_traversal(tmp_app_data_dir):
    response = client.post(
        "/write_file?file_path=../evil.txt", json={"content": "malicious"}
    )
    assert response.status_code == 400
    assert "Path traversal detected" in response.json()["detail"]


def test_write_file_invalid_extension(tmp_app_data_dir):
    response = client.post(
        "/write_file?file_path=document.pdf", json={"content": "pdf content"}
    )
    assert response.status_code == 400
    assert "Extension .pdf not allowed" in response.json()["detail"]


def test_write_file_payload_too_large(tmp_app_data_dir):
    large_content = "A" * (MAX_FILE_SIZE_BYTES + 1)  # Exceeds limit
    response = client.post(
        "/write_file?file_path=large_file.txt", json={"content": large_content}
    )
    assert response.status_code == 413
    assert "File size exceeds" in response.json()["detail"]


def test_read_file_not_utf8(tmp_app_data_dir):
    # Create a file with non-UTF-8 content
    non_utf8_path = tmp_app_data_dir / "non_utf8.txt"
    with open(non_utf8_path, "wb") as f:
        f.write(b"\x80")  # Invalid UTF-8 byte

    response = client.get(f"/read_file?file_path={non_utf8_path.name}")
    assert response.status_code == 400
    assert "File is not UTF-8 encoded" in response.json()["detail"]


def test_trace_id_propagation(tmp_app_data_dir):
    trace_id_value = "12345-abcde"
    file_path = "trace_test.txt"
    file_content = "Content with trace"

    # Test write with trace_id
    response = client.post(
        f"/write_file?file_path={file_path}",
        json={"content": file_content},
        headers={"X-Trace-ID": trace_id_value},
    )
    assert response.status_code == 200

    # Test read with trace_id
    response = client.get(
        f"/read_file?file_path={file_path}", headers={"X-Trace-ID": trace_id_value}
    )
    assert response.status_code == 200
    assert response.json()["content"] == file_content

    # Test list with trace_id
    response = client.get("/list_files", headers={"X-Trace-ID": trace_id_value})
    assert response.status_code == 200
    assert "trace_test.txt" in response.json()["files"]
