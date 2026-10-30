
import shutil
from pathlib import Path
from uuid import UUID

# All temporary consultation files go inside this directory.
BASE_DIR = Path(__file__).resolve().parent
TEMP_ROOT = BASE_DIR / "temp_uploads"


def delete_consultation_files(session_id: str) -> bool:
    """Delete temporary files for one consultation session."""

    try:
        # Validate the ID so it cannot be used as a filesystem path.
        safe_id = str(UUID(session_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid consultation session ID")

    session_dir = TEMP_ROOT / safe_id

    if not session_dir.exists():
        return False

    # Delete the session's temporary directory and its contents.
    shutil.rmtree(session_dir)
    return True
