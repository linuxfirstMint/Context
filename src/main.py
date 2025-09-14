import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI()

# Configuration constants
ALLOWED_EXTENSIONS = {".txt", ".log", ".md", ".py", ".json", ".yml", ".yaml"}
MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB
BASE_DIR = Path(__file__).parent.parent / "app_data"

# Ensure BASE_DIR exists
BASE_DIR.mkdir(parents=True, exist_ok=True)


# Dependency to get trace_id
async def get_trace_id(x_trace_id: str | None = Header(None)):
    return x_trace_id


# Pydantic models for request/response bodies
class FileContent(BaseModel):
    content: str = Field(..., description="File content in UTF-8")


class FileListResponse(BaseModel):
    files: list[str] = Field(..., description="List of files")


# Helper function for path validation
def validate_path(file_path: str) -> Path:
    # Resolve the path to prevent directory traversal
    abs_path = (BASE_DIR / file_path).resolve()
    if not abs_path.is_relative_to(BASE_DIR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal detected"
        )
    return abs_path


# Helper function for extension validation
def validate_extension(file_path: Path):
    if file_path.suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extension {file_path.suffix} not allowed",
        )


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/list_files")
async def list_files(
    extensions: str | None = None,
    max_items: int | None = None,
    trace_id: str = Depends(get_trace_id),
) -> FileListResponse:
    """
    Lists files within the BASE_DIR, optionally filtered by extensions and limited by max_items.
    """
    all_files = []
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            relative_path = Path(root) / file
            try:
                # Ensure the path is relative to BASE_DIR for consistent output
                relative_path_str = str(relative_path.relative_to(BASE_DIR))
                all_files.append(relative_path_str)
            except ValueError:
                # This should not happen if os.walk starts from BASE_DIR
                continue

    # Filter by extensions
    if extensions:
        allowed_extensions_list = [ext.strip() for ext in extensions.split(",")]
        all_files = [f for f in all_files if Path(f).suffix in allowed_extensions_list]

    # Limit by max_items
    if max_items is not None:
        all_files = all_files[:max_items]

    return FileListResponse(files=all_files)


@app.get("/read_file")
async def read_file(
    file_path: str, trace_id: str = Depends(get_trace_id)
) -> FileContent:
    """
    Reads the content of a specified file.
    """
    abs_path = validate_path(file_path)
    validate_extension(abs_path)

    if not abs_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        with open(abs_path, encoding="utf-8") as f:
            content = f.read()
        return FileContent(content=content)
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is not UTF-8 encoded"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {e}",
        )


@app.post("/write_file")
async def write_file(
    file_path: str, file_content: FileContent, trace_id: str = Depends(get_trace_id)
) -> Response:
    """
    Writes content to a specified file.
    """
    abs_path = validate_path(file_path)
    validate_extension(abs_path)

    # Check file size limit
    if len(file_content.content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_BYTES / 1024}KB limit",
        )

    try:
        # Ensure parent directories exist
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(file_content.content)
        return Response(
            status_code=status.HTTP_200_OK, content="File written successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error writing file: {e}",
        )
