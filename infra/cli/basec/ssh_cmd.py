"""SSH command - connect to droplets via SSH."""

import subprocess
import sys

import typer

from basec.inventory import get_droplet, get_inventory_path
from basec.output import print_error

app = typer.Typer()


@app.command()
def ssh(
    droplet: str = typer.Argument(..., help="Droplet name (e.g., 'edge', 'platform', 'vertical_construction')"),
    command: str = typer.Argument(None, help="Command to execute (optional, opens interactive shell if not provided)"),
) -> None:
    """Connect to a droplet via SSH or execute a command."""
    droplet_config = get_droplet(droplet)
    
    if not droplet_config:
        print_error(f"Droplet '{droplet}' not found in inventory")
        sys.exit(1)
    
    inventory_path = get_inventory_path()
    key_path = inventory_path.parent / "deploy_key"
    
    try:
        if command:
            # Execute single command via SSH
            from basec.ssh import SSHClientWrapper
            
            ssh_client = SSHClientWrapper(host=droplet_config.ip, user=droplet_config.user)
            ssh_client.connect()
            exit_code, stdout, stderr = ssh_client.execute(command, check=False, capture_output=False)
            ssh_client.disconnect()
            sys.exit(exit_code)
        else:
            # Interactive shell using subprocess
            cmd = [
                "ssh",
                "-i", str(key_path),
                f"{droplet_config.user}@{droplet_config.ip}",
            ]
            subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n")
        sys.exit(130)
    except Exception as e:
        print_error(f"SSH connection failed: {e}")
        sys.exit(1)



