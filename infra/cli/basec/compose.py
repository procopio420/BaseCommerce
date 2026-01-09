"""Docker Compose operations - down, restart, etc."""

import sys

import typer

from basec.docker import DockerCompose
from basec.inventory import (
    get_droplet,
    get_droplets_by_role,
    list_droplets,
)
from basec.output import (
    print_error,
    print_header,
    print_section,
    print_success,
    spinner,
)

app = typer.Typer()


@app.command()
def down(
    droplet: str = typer.Argument(None, help="Droplet name (optional, stops all if not provided)"),
    vertical: str = typer.Option(None, "--vertical", "-v", help="Vertical name (if droplet is 'vertical')"),
) -> None:
    """Stop and remove containers."""
    if droplet:
        droplet_config = get_droplet(droplet)
        if not droplet_config:
            if droplet == "vertical" and vertical:
                droplet_config = get_droplet(f"vertical_{vertical}")
            else:
                print_error(f"Droplet '{droplet}' not found")
                sys.exit(1)
        
        if not droplet_config:
            print_error(f"Droplet not found")
            sys.exit(1)
        
        print_header(f"Stopping: {droplet} ({droplet_config.ip})")
        docker = DockerCompose(droplet_config)
        with spinner("Stopping containers..."):
            docker.down()
        print_success(f"Containers stopped for {droplet}")
    else:
        # Stop all droplets
        print_header("Stopping All Droplets")
        droplets = list_droplets()
        
        # Stop in reverse order: verticals, edge, platform
        vertical_droplets = {k: v for k, v in droplets.items() if v.role == "vertical"}
        for name, config in vertical_droplets.items():
            print_section(f"Stopping: {name} ({config.ip})")
            docker = DockerCompose(config)
            with spinner("Stopping containers..."):
                docker.down()
            print_success(f"Containers stopped for {name}")
        
        edge_droplets = {k: v for k, v in droplets.items() if v.role == "edge"}
        for name, config in edge_droplets.items():
            print_section(f"Stopping: {name} ({config.ip})")
            docker = DockerCompose(config)
            with spinner("Stopping containers..."):
                docker.down()
            print_success(f"Containers stopped for {name}")
        
        platform_droplets = {k: v for k, v in droplets.items() if v.role == "platform"}
        for name, config in platform_droplets.items():
            print_section(f"Stopping: {name} ({config.ip})")
            docker = DockerCompose(config)
            with spinner("Stopping containers..."):
                docker.down()
            print_success(f"Containers stopped for {name}")


@app.command()
def restart(
    droplet: str = typer.Argument(..., help="Droplet name"),
    service: str = typer.Argument(None, help="Service name (optional, restarts all if not provided)"),
    vertical: str = typer.Option(None, "--vertical", "-v", help="Vertical name (if droplet is 'vertical')"),
) -> None:
    """Restart services."""
    droplet_config = get_droplet(droplet)
    if not droplet_config:
        if droplet == "vertical" and vertical:
            droplet_config = get_droplet(f"vertical_{vertical}")
        else:
            print_error(f"Droplet '{droplet}' not found")
            sys.exit(1)
    
    if not droplet_config:
        print_error(f"Droplet not found")
        sys.exit(1)
    
    print_header(f"Restarting: {droplet} ({droplet_config.ip})")
    docker = DockerCompose(droplet_config)
    
    with spinner(f"Restarting {service or 'all services'}..."):
        docker.restart(service)
    
    print_success(f"Services restarted for {droplet}")


