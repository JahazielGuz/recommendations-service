import argparse
from importlib.resources import files

from recs.config import load_settings, required
from recs.db import connect
from recs.ingest import rebuild


def migrate() -> None:
    """Apply the schema. Idempotent, and the only command that needs no OpenAI key."""
    schema = files("recs").joinpath("schema.sql").read_text(encoding="utf-8")

    # vectors=False because registering pgvector's type needs an extension this is about to create
    with connect(required("DATABASE_URL"), vectors=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema)

    print("schema applied")


def main() -> None:
    parser = argparse.ArgumentParser(prog="recs", description="webshow similar titles")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="create the extension, the table and the index")
    commands.add_parser("rebuild", help="embed every movie whose document or model changed")

    arguments = parser.parse_args()

    if arguments.command == "migrate":
        migrate()
        return

    report = rebuild(load_settings())
    print(
        f"catalogue {report.catalogue}, embedded {report.embedded}, "
        f"unchanged {report.unchanged}, removed {report.removed}"
    )
