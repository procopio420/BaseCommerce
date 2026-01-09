"""BaseCommerce Infrastructure CLI - Main entrypoint."""

import sys

import typer

from basec import compose, deploy, firewall, logs, migrate, rollback, smoke, ssh_cmd, ssl, status, tenants

app = typer.Typer(
    name="basec",
    help="BaseCommerce Infrastructure CLI - Gerencia droplets, containers, deploys e tenants",
    add_completion=False,
)

# Global env option - available to all commands
def get_env_callback(ctx: typer.Context, env: str = "production") -> str:
    """Global --env option callback."""
    return env

# Register commands
def status_wrapper(env: str = typer.Option("production", "--env", "-e", help="Environment name")):
    """Status command wrapper."""
    return status.status_command(env)

app.command(name="status")(status_wrapper)

# Smoke command - extract from typer app to add env support
def smoke_wrapper(
    target: str = typer.Argument(None, help="Target: 'edge', 'platform', 'vertical', or 'all'"),
    vertical_name: str = typer.Option(None, "--vertical", "-v", help="Vertical name"),
    env: str = typer.Option("production", "--env", "-e", help="Environment name"),
):
    """Run smoke tests."""
    from basec.smoke import smoke
    return smoke(target, vertical_name, env)

app.command(name="smoke")(smoke_wrapper)
app.command(name="logs")(logs.logs_command)  # Direct command, not subcommand
app.command(name="deploy")(deploy.deploy)  # Direct command, not subcommand
app.command(name="rollback")(rollback.rollback)  # Direct command, not subcommand
app.add_typer(tenants.app, name="tenants")
app.add_typer(ssh_cmd.app, name="ssh")
app.add_typer(migrate.app, name="migrate")
app.add_typer(compose.app, name="compose")
app.add_typer(firewall.app, name="firewall")
app.add_typer(ssl.app, name="ssl")


def main() -> None:
    """Main entrypoint for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        print("\n")
        sys.exit(130)
    except Exception as e:
        from basec.output import print_error
        
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

