"""Initialize and safely verify the persistent local JustiFi database."""

import sqlite3
import sys

try:
    from . import database
except ImportError:
    import database


def main() -> int:
    try:
        path = database.initialize_database()
        database.check_database()
        with database.connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM legal_sources"
            ).fetchone()[0]
        print("SQLite health: PASS")
        print(f"Database file exists: {path.is_file()}")
        print(f"Legal source records: {count}")
        return 0
    except (sqlite3.Error, OSError, RuntimeError, ValueError) as error:
        print(f"SQLite health: FAIL ({type(error).__name__})")
        print("Check JUSTIFI_DB_PATH permissions and available disk space.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
