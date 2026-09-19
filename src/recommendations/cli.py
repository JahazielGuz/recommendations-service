import argparse
from importlib.resources import files

from recommendations.config import required
from recommendations.db import connect

VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migration (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

def Migrate() -> None:
  """Apply every migration this database has not seen, oldest first."""
  directory = files("recommendations").joinpath("migrations")
  scripts = sorted((path for path in directory.iterdir() if path.name.endswith(".sql")),
  key=lambda path: path.name)

  with connect(required("DATABASE_URL"), vectors=False) as connection:
    with connection.cursor() as cursor:
      cursor.execute(VERSION_TABLE)
      cursor.execute("SELECT version FROM schema_migration")
      applied = {row[0] for row in cursor.fetchall()}

    pending = [script for script in scripts if script.name not in applied]

    for script in pending:
      with connection.cursor() as cursor:
        cursor.execute(script.read_text(encoding="utf-8"))
        cursor.execute("INSERT INTO schema_migration (version) VALUES (%s)", (script.name,))

  print(f"applied {len(pending)} migration(s)" if pending else "already up to date")

def main() -> None:
  parser = argparse.ArgumentParser(prog="recommendations", description="webshow retrieval")
  commands = parser.add_subparsers(dest="command", required=True)
  commands.add_parser("migrate", help="apply pending migrations")

  arguments = parser.parse_args()

  if arguments.command == "migrate":
    migrate()
