import typer
from . import config
from . import backup
from . import restore

app = typer.Typer()


@app.command()
def validate_config():
    """Validate required environment variables and configuration."""
    cfg = config.validate_env()
    typer.echo("Configuration format looks good.")

    # Proactively check Neon connectivity
    import psycopg

    typer.echo("Checking connection to Neon database...")
    try:
        with psycopg.connect(cfg.neon_database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        typer.echo("Successfully connected to Neon database.")
    except Exception as e:
        typer.echo(f"Connectivity check failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def backup_run():
    """Run a backup and restore to Neon branch."""
    backup.run()


@app.command()
def restore_test():
    """Run a restore test using the latest backup."""
    restore.run_restore_test()


@app.command()
def enable_uuid_extension(schema: str = typer.Option("public", help="Schema to create the extension in")):
    """Enable uuid-ossp extension in the specified schema."""
    import psycopg

    cfg = config.validate_env()

    typer.echo(f"Enabling uuid-ossp extension in schema '{schema}'...")
    try:
        with psycopg.connect(cfg.neon_database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA {schema}')
        typer.echo(f"✓ uuid-ossp extension is now available in schema '{schema}'")
    except Exception as e:
        typer.echo(f"Failed to enable extension: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
