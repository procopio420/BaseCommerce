"""Migration commands - manage database migrations."""

import sys

import typer

from basec.docker import DockerCompose
from basec.inventory import get_droplet, get_droplets_by_role
from basec.output import (
    confirm,
    print_error,
    print_header,
    print_section,
    print_success,
    spinner,
)

app = typer.Typer()


def get_vertical_droplet(vertical_name: str = "construction"):
    """Get vertical droplet for migrations."""
    droplet_name = f"vertical_{vertical_name}"
    droplet = get_droplet(droplet_name)
    
    if not droplet:
        # Try to find any vertical
        verticals = get_droplets_by_role("vertical")
        if not verticals:
            raise RuntimeError("No vertical droplets found in inventory")
        droplet = next(iter(verticals.values()))
    
    return droplet, droplet.vertical or "construction"


@app.command()
def status(
    vertical: str = typer.Option("construction", "--vertical", "-v", help="Vertical name"),
) -> None:
    """Show current migration status."""
    print_header("Database Migration Status")
    
    try:
        droplet_config, service_name = get_vertical_droplet(vertical)
        docker = DockerCompose(droplet_config)
        
        print_section("Current revision:")
        current = docker.exec(
            service_name,
            "alembic current",
            capture_output=True,
        )
        if current.strip():
            print(current)
        else:
            print("No migrations applied yet")
        
        print()
        print_section("Migration history:")
        history = docker.exec(
            service_name,
            "alembic history --verbose",
            capture_output=True,
        )
        if history.strip():
            print(history)
        else:
            print("No history available")
    
    except Exception as e:
        print_error(f"Failed to get migration status: {e}")
        sys.exit(1)


@app.command()
def apply(
    vertical: str = typer.Option("construction", "--vertical", "-v", help="Vertical name"),
) -> None:
    """Apply pending migrations."""
    print_header("Applying Database Migrations")
    
    try:
        droplet_config, service_name = get_vertical_droplet(vertical)
        docker = DockerCompose(droplet_config)
        
        print_section("Current status:")
        current = docker.exec(service_name, "alembic current", capture_output=True)
        print(current if current.strip() else "No migrations applied yet")
        
        print()
        print_section("Applying migrations...")
        with spinner("Running alembic upgrade head..."):
            output = docker.exec(service_name, "alembic upgrade head", capture_output=False)
        
        print()
        print_section("Final status:")
        final = docker.exec(service_name, "alembic current", capture_output=True)
        print(final)
        
        print()
        print_success("Migrations applied successfully")
    
    except Exception as e:
        print_error(f"Failed to apply migrations: {e}")
        sys.exit(1)


@app.command()
def rollback(
    steps: str = typer.Argument("1", help="Number of steps to rollback, or 'base' to rollback all"),
    vertical: str = typer.Option("construction", "--vertical", "-v", help="Vertical name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Rollback migrations."""
    if steps == "base":
        target = "base"
        warning = "This will rollback ALL migrations!"
    else:
        try:
            num_steps = int(steps)
            target = f"-{num_steps}"
            warning = f"This will rollback {num_steps} migration(s)"
        except ValueError:
            print_error(f"Invalid steps value: {steps}. Use a number or 'base'")
            sys.exit(1)
    
    print_header("Rollback Database Migrations")
    
    if not yes:
        if not confirm(f"{warning}. Continue?", default=False):
            print("Cancelled.")
            sys.exit(0)
    
    try:
        droplet_config, service_name = get_vertical_droplet(vertical)
        docker = DockerCompose(droplet_config)
        
        print_section("Current status before rollback:")
        current = docker.exec(service_name, "alembic current", capture_output=True)
        print(current)
        
        print()
        print_section("Rolling back...")
        with spinner(f"Running alembic downgrade {target}..."):
            docker.exec(service_name, f"alembic downgrade {target}", capture_output=False)
        
        print()
        print_section("Status after rollback:")
        final = docker.exec(service_name, "alembic current", capture_output=True)
        print(final)
        
        print()
        print_success("Rollback complete!")
    
    except Exception as e:
        print_error(f"Failed to rollback migrations: {e}")
        sys.exit(1)


@app.command()
def reset(
    vertical: str = typer.Option("construction", "--vertical", "-v", help="Vertical name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Reset database (drop all tables and run migrations from scratch).
    
    WARNING: This will DELETE ALL DATA in the database!
    """
    print_header("Reset Database")
    
    if not yes:
        if not confirm("This will DELETE ALL DATA in the database! Continue?", default=False):
            print("Cancelled.")
            sys.exit(0)
    
    try:
        # Get platform droplet for PostgreSQL
        platform_droplets = get_droplets_by_role("platform")
        if not platform_droplets:
            raise RuntimeError("No platform droplet found in inventory")
        platform = next(iter(platform_droplets.values()))
        platform_docker = DockerCompose(platform)
        
        # Get vertical droplet for migrations
        droplet_config, service_name = get_vertical_droplet(vertical)
        vertical_docker = DockerCompose(droplet_config)
        
        print_section("[1/3] Dropping all tables...")
        with spinner("Dropping schema..."):
            platform_docker.exec(
                "postgres",
                "psql -U basecommerce -d basecommerce -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'",
                capture_output=False,
            )
        
        print()
        print_section("[2/3] Running migrations from scratch...")
        with spinner("Running alembic upgrade head..."):
            vertical_docker.exec(service_name, "alembic upgrade head", capture_output=False)
        
        print()
        print_section("[3/3] Verifying migration status...")
        current = vertical_docker.exec(service_name, "alembic current", capture_output=True)
        print(current)
        
        print()
        print_success("Database reset complete!")
    
    except Exception as e:
        print_error(f"Failed to reset database: {e}")
        sys.exit(1)




