"""Backup orchestration: fetch collections from MongoDB, store in Neon as JSONB."""

from __future__ import annotations

import datetime
import json
import psycopg
import pymongo  # type: ignore
from typing import Any, Optional
from bson import ObjectId  # type: ignore

from .config import validate_env


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)


def list_backup_schemas(conn_url: str) -> list[str]:
    """List all schemas in Neon that start with 'backup_'."""
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'backup_%' ORDER BY schema_name ASC"
            )
            return [row[0] for row in cur.fetchall()]


def delete_schema(conn_url: str, schema_name: str) -> None:
    """Delete a schema and all its contents."""
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


def run(mongodb_url: Optional[str] = None, neon_url: Optional[str] = None):
    cfg = validate_env()
    mongodb_url = mongodb_url or cfg.mongodb_srv_url
    neon_url = neon_url or cfg.neon_database_url

    # Rotation Policy: Max 6 backup schemas.
    print("Checking rotation policy...")
    backup_schemas = list_backup_schemas(neon_url)

    max_schemas = 6
    while len(backup_schemas) >= max_schemas:
        oldest = backup_schemas.pop(0)
        print(f"Rotation: deleting old schema {oldest}...")
        try:
            delete_schema(neon_url, oldest)
        except Exception as e:
            print(f"WARNING: Failed to delete old schema {oldest}: {e}")

    new_schema = f"backup_{_timestamp()}"
    print(f"Creating backup schema {new_schema}...")

    with psycopg.connect(neon_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{new_schema}"')

    print(f"Starting MongoDB backup from {mongodb_url}...")

    # Connect to MongoDB
    client: Any = pymongo.MongoClient(mongodb_url)
    try:
        # Ping check
        client.admin.command("ping")
        print("Connected to MongoDB successfully.")

        # Get database name from URL or default to 'primary'
        db_name = pymongo.uri_parser.parse_uri(mongodb_url).get("database") or "test"
        db = client[db_name]
        collections = db.list_collection_names()

        print(
            f"Found {len(collections)} collections in database '{db_name}': {', '.join(collections)}"
        )

        with psycopg.connect(neon_url) as pg_conn:
            with pg_conn.cursor() as pg_cur:
                # Set search_path to the new schema
                pg_cur.execute(f'SET search_path TO "{new_schema}"')

                for coll_name in collections:
                    print(f"Backing up collection '{coll_name}'...")

                    # Create table for this collection
                    pg_cur.execute(
                        f'CREATE TABLE "{coll_name}" (id SERIAL PRIMARY KEY, data JSONB, created_at TIMESTAMPTZ DEFAULT NOW())'
                    )

                    # Fetch all documents and insert into Postgres
                    coll = db[coll_name]
                    docs = list(coll.find())

                    if docs:
                        # Prepare data for batch insert
                        # Use our custom encoder to handle ObjectId and datetimes
                        json_docs = [
                            json.dumps(doc, cls=MongoJSONEncoder) for doc in docs
                        ]

                        # Batch insert
                        query = f'INSERT INTO "{coll_name}" (data) VALUES (%s)'
                        pg_cur.executemany(query, [(d,) for d in json_docs])

                    print(f"  Done: {len(docs)} documents backed up.")

            pg_conn.commit()

        print(f"Backup completed successfully in schema {new_schema}.")

    finally:
        client.close()
        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
