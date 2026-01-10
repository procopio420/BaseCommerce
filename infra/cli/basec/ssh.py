"""SSH client wrapper using Paramiko."""

import os
import select
import sys
from pathlib import Path
from typing import Iterator, Optional

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from basec.inventory import get_inventory_path
from basec.output import print_error


class SSHClientWrapper:
    """Wrapper for SSH operations using Paramiko."""
    
    # Default command timeout (can be overridden per command)
    default_command_timeout = 300
    
    def __init__(
        self,
        host: str,
        user: str = "root",
        key_path: Optional[Path] = None,
        timeout: int = 10,
    ):
        """Initialize SSH client.
        
        Args:
            host: Hostname or IP address
            user: SSH username
            key_path: Path to SSH private key (defaults to infra/deploy_key)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.user = user
        self.timeout = timeout
        
        # Default to infra/deploy_key relative to inventory.yaml
        if key_path is None:
            inventory_path = get_inventory_path()
            key_path = inventory_path.parent / "deploy_key"
        
        self.key_path = key_path
        
        if not self.key_path.exists():
            raise FileNotFoundError(f"SSH key not found: {self.key_path}")
        
        self.client: Optional[SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
    
    def connect(self) -> None:
        """Establish SSH connection."""
        if self.client is not None:
            return
        
        try:
            self.client = SSHClient()
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            
            # Try to load private key - support multiple formats
            key = None
            key_errors = []
            
            # Try different key types
            key_loaders = [
                ("RSA", lambda: paramiko.RSAKey.from_private_key_file(str(self.key_path))),
                ("ED25519", lambda: paramiko.Ed25519Key.from_private_key_file(str(self.key_path))),
                ("ECDSA", lambda: paramiko.ECDSAKey.from_private_key_file(str(self.key_path))),
                ("DSS", lambda: paramiko.DSSKey.from_private_key_file(str(self.key_path))),
            ]
            
            for key_type, loader in key_loaders:
                try:
                    key = loader()
                    break
                except Exception as e:
                    key_errors.append(f"{key_type}: {str(e)}")
                    continue
            
            if key is None:
                # Last resort: try with password=None
                try:
                    key = paramiko.RSAKey.from_private_key_file(str(self.key_path), password=None)
                except Exception:
                    raise ValueError(
                        f"Could not load SSH key from {self.key_path}. "
                        f"Tried: {', '.join([k[0] for k in key_loaders])}. "
                        f"Errors: {'; '.join(key_errors[:2])}"
                    )
            
            self.client.connect(
                hostname=self.host,
                username=self.user,
                pkey=key,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        except Exception as e:
            self.client = None
            raise ConnectionError(f"Failed to connect to {self.user}@{self.host}: {e}")
    
    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        
        if self.client:
            self.client.close()
            self.client = None
    
    def check_connection(self, timeout: int = 5) -> bool:
        """Check if connection is possible (quick check)."""
        try:
            test_client = SSHClient()
            test_client.set_missing_host_key_policy(AutoAddPolicy())
            
            # Try to load private key - support multiple formats
            key = None
            key_loaders = [
                ("RSA", lambda: paramiko.RSAKey.from_private_key_file(str(self.key_path))),
                ("ED25519", lambda: paramiko.Ed25519Key.from_private_key_file(str(self.key_path))),
                ("ECDSA", lambda: paramiko.ECDSAKey.from_private_key_file(str(self.key_path))),
                ("DSS", lambda: paramiko.DSSKey.from_private_key_file(str(self.key_path))),
            ]
            
            for key_type, loader in key_loaders:
                try:
                    key = loader()
                    break
                except Exception:
                    continue
            
            if key is None:
                # Last resort: try with password=None
                try:
                    key = paramiko.RSAKey.from_private_key_file(str(self.key_path), password=None)
                except Exception:
                    return False
            
            test_client.connect(
                hostname=self.host,
                username=self.user,
                pkey=key,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            test_client.close()
            return True
        except Exception:
            return False
    
    def execute(
        self,
        command: str,
        check: bool = True,
        capture_output: bool = False,
        timeout: Optional[int] = None,
    ) -> tuple[int, str, str]:
        """Execute a command on the remote host.
        
        Args:
            command: Command to execute
            check: Raise exception if command fails
            capture_output: Capture stdout/stderr instead of printing
            timeout: Command timeout in seconds (default: default_command_timeout)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if self.client is None:
            self.connect()
        
        if timeout is None:
            timeout = self.default_command_timeout
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8")
            stderr_text = stderr.read().decode("utf-8")
            
            if check and exit_code != 0:
                raise RuntimeError(
                    f"Command failed with exit code {exit_code}:\n"
                    f"Command: {command}\n"
                    f"Stderr: {stderr_text}"
                )
            
            if not capture_output:
                if stdout_text:
                    print(stdout_text, end="")
                if stderr_text and exit_code != 0:
                    print_error(stderr_text)
            
            return exit_code, stdout_text, stderr_text
        except Exception as e:
            if check:
                raise
            return 1, "", str(e)
    
    def execute_stream(
        self,
        command: str,
        timeout: Optional[int] = None,
        pty: bool = False,
    ) -> int:
        """Execute a command with streaming output in real-time.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default: default_command_timeout)
            pty: Allocate a pseudo-terminal (useful for interactive commands)
        
        Returns:
            Exit code of the command
        
        Raises:
            TimeoutError: If command exceeds timeout
        """
        if self.client is None:
            self.connect()
        
        if timeout is None:
            timeout = self.default_command_timeout
        
        try:
            transport = self.client.get_transport()
            if transport is None:
                raise RuntimeError("SSH transport not available")
            
            channel = transport.open_session()
            
            if pty:
                # Request pseudo-terminal
                channel.get_pty()
            
            channel.exec_command(command)
            
            # Read output incrementally
            import time
            start_time = time.time()
            
            while not channel.exit_status_ready():
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    channel.close()
                    raise TimeoutError(f"Command exceeded timeout of {timeout}s: {command}")
                
                # Check if data is available
                if channel.recv_ready():
                    data = channel.recv(4096).decode("utf-8", errors="replace")
                    if data:
                        print(data, end="", flush=True)
                
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    if data:
                        print_error(data, end="", flush=True)
                
                # Small sleep to avoid busy waiting
                time.sleep(0.1)
            
            # Get exit status
            exit_code = channel.recv_exit_status()
            
            # Read any remaining data
            while channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                if data:
                    print(data, end="", flush=True)
            
            while channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                if data:
                    print_error(data, end="", flush=True)
            
            channel.close()
            return exit_code
            
        except TimeoutError:
            raise
        except Exception as e:
            raise RuntimeError(f"Stream execution failed: {e}")
    
    def execute_lines(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> Iterator[str]:
        """Execute a command and yield output line by line.
        
        Useful for polling scenarios where you need to process output incrementally.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (default: default_command_timeout)
        
        Yields:
            Lines of stdout as they become available
        """
        if self.client is None:
            self.connect()
        
        if timeout is None:
            timeout = self.default_command_timeout
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            # Read line by line
            for line in stdout:
                yield line.rstrip("\n\r")
            
            # Wait for exit status
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                stderr_text = stderr.read().decode("utf-8")
                raise RuntimeError(
                    f"Command failed with exit code {exit_code}:\n"
                    f"Command: {command}\n"
                    f"Stderr: {stderr_text}"
                )
        except Exception as e:
            raise RuntimeError(f"Line execution failed: {e}")
    
    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Upload a file to the remote host."""
        if self.client is None:
            self.connect()
        
        if not self.sftp:
            self.sftp = self.client.open_sftp()
        
        try:
            # Ensure remote directory exists
            remote_dir = "/".join(remote_path.split("/")[:-1])
            if remote_dir:
                self.execute(f"mkdir -p {remote_dir}", check=False)
            
            self.sftp.put(str(local_path), remote_path)
        except Exception as e:
            raise RuntimeError(f"Failed to upload {local_path} to {remote_path}: {e}")
    
    def upload_directory(self, local_dir: Path, remote_base: str) -> None:
        """Upload a directory recursively to the remote host.
        
        Args:
            local_dir: Local directory path to upload
            remote_base: Remote base directory path (directory will be created/uploaded here)
        """
        if self.client is None:
            self.connect()
        
        if not self.sftp:
            self.sftp = self.client.open_sftp()
        
        if not local_dir.is_dir():
            raise ValueError(f"{local_dir} is not a directory")
        
        # Ensure remote base directory exists
        self.execute(f"mkdir -p {remote_base}", check=False)
        
        # Walk local directory and upload files
        for local_path in local_dir.rglob("*"):
            if local_path.is_file():
                # Get relative path from local_dir
                rel_path = local_path.relative_to(local_dir)
                remote_path = f"{remote_base}/{rel_path.as_posix()}"
                
                # Ensure remote directory exists
                remote_dir = "/".join(remote_path.split("/")[:-1])
                if remote_dir:
                    self.execute(f"mkdir -p {remote_dir}", check=False)
                
                # Upload file
                try:
                    self.sftp.put(str(local_path), remote_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to upload {local_path} to {remote_path}: {e}")
    
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from the remote host."""
        if self.client is None:
            self.connect()
        
        if not self.sftp:
            self.sftp = self.client.open_sftp()
        
        try:
            self.sftp.get(remote_path, str(local_path))
        except Exception as e:
            raise RuntimeError(f"Failed to download {remote_path} to {local_path}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
