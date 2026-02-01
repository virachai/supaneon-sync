import typer
from . import config
from . import backup
from . import restore
from . import healthcheck

app = typer.Typer()

@app.command()
def validate_config():
    """Validate required environment variables and configuration."""
    config.validate_env()
    typer.echo("Configuration looks good.")

@app.command()
def backup_run():
    """Run a backup and restore to Neon branch."""
    backup.run()

@app.command()
def restore_test():
    """Run a restore test using the latest backup."""
    restore.run_restore_test()

if __name__ == "__main__":
    app()
