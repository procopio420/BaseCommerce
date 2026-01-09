"""Firewall (UFW) status and management."""

import sys

import typer

from basec.inventory import list_droplets
from basec.output import (
    print_error,
    print_header,
    print_section,
)
from basec.ssh import SSHClientWrapper

app = typer.Typer()


@app.command()
def status() -> None:
    """Show UFW firewall status on all droplets."""
    print_header("UFW Firewall Status")
    
    droplets = list_droplets()
    
    for name, config in droplets.items():
        print_section(f"{name.upper()} ({config.ip})")
        
        ssh = SSHClientWrapper(host=config.ip, user=config.user)
        
        try:
            if ssh.check_connection(timeout=5):
                ssh.connect()
                exit_code, stdout, stderr = ssh.execute(
                    "ufw status verbose",
                    check=False,
                    capture_output=True,
                )
                if exit_code == 0:
                    print(stdout)
                else:
                    print_error("UFW not available or not configured")
                ssh.disconnect()
            else:
                print_error("Cannot connect via SSH")
        except Exception as e:
            print_error(f"Error: {e}")


