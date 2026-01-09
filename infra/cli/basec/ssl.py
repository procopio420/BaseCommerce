"""SSL command - manage SSL certificates for edge droplets."""

import os
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Optional

import typer

from basec.docker import DockerCompose
from basec.inventory import get_droplet, get_inventory_path
from basec.output import (
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
    print_warning,
    spinner,
)

app = typer.Typer()


def validate_certificates(docker: DockerCompose) -> tuple[bool, str]:
    """Validate if SSL certificates exist and are readable.
    
    Note: Assumes SSH connection is already established.
    
    Returns:
        Tuple of (is_valid, message)
    """
    remote_dir = docker.remote_dir
    
    # Check if certificate files exist
    cert_path = f"{remote_dir}/nginx/ssl/origin.pem"
    key_path = f"{remote_dir}/nginx/ssl/origin.key"
    
    exit_code_cert, stdout_cert, _ = docker.ssh.execute(
        f"test -f {shlex.quote(cert_path)} && echo 'EXISTS' || echo 'NOT_FOUND'",
        check=False,
        capture_output=True,
    )
    
    exit_code_key, stdout_key, _ = docker.ssh.execute(
        f"test -f {shlex.quote(key_path)} && echo 'EXISTS' || echo 'NOT_FOUND'",
        check=False,
        capture_output=True,
    )
    
    cert_exists = "EXISTS" in stdout_cert
    key_exists = "EXISTS" in stdout_key
    
    if not cert_exists or not key_exists:
        missing = []
        if not cert_exists:
            missing.append("origin.pem")
        if not key_exists:
            missing.append("origin.key")
        return False, f"Missing certificate files: {', '.join(missing)}"
    
    # Check permissions
    exit_code_perm, stdout_perm, _ = docker.ssh.execute(
        f"ls -l {shlex.quote(key_path)} 2>/dev/null | awk '{{print $1}}' || echo ''",
        check=False,
        capture_output=True,
    )
    
    if stdout_perm.strip() and "rw-------" not in stdout_perm and "-rw-------" not in stdout_perm:
        return False, "Private key (origin.key) should have permissions 600 (rw-------)"
    
    # Validate certificate content (basic check)
    exit_code_valid, stdout_valid, _ = docker.ssh.execute(
        f"openssl x509 -in {shlex.quote(cert_path)} -text -noout > /dev/null 2>&1 && echo 'VALID' || echo 'INVALID'",
        check=False,
        capture_output=True,
    )
    
    if "VALID" not in stdout_valid:
        return False, "Certificate file (origin.pem) is not a valid X.509 certificate"
    
    # Check certificate expiration (basic)
    exit_code_date, stdout_date, _ = docker.ssh.execute(
        f"openssl x509 -in {shlex.quote(cert_path)} -noout -enddate 2>/dev/null | cut -d= -f2 || echo ''",
        check=False,
        capture_output=True,
    )
    
    if stdout_date.strip():
        return True, f"Certificates valid (expires: {stdout_date.strip()})"
    
    return True, "Certificates exist and are valid"


@app.command()
def check(
    droplet: str = typer.Argument("edge", help="Droplet name (default: edge)"),
) -> None:
    """Check SSL certificate status on edge droplet."""
    print_header("SSL Certificate Status")
    
    droplet_config = get_droplet(droplet)
    if not droplet_config:
        print_error(f"Droplet '{droplet}' not found")
        sys.exit(1)
    
    if droplet_config.role != "edge":
        print_warning(f"Droplet '{droplet}' is not an edge droplet (role: {droplet_config.role})")
        print_warning("SSL certificates are typically only needed for edge droplets")
    
    docker = DockerCompose(droplet_config)
    
    with spinner("Checking certificates..."):
        docker.ssh.connect()
        is_valid, message = validate_certificates(docker)
        docker.ssh.disconnect()
    
    print_section("Certificate Status")
    if is_valid:
        print_success(f"✓ {message}")
        
        # Check nginx SSL configuration
        with spinner("Checking nginx SSL configuration..."):
            docker.ssh.connect()
            exit_code, stdout, stderr = docker._run_compose(
                "exec -T nginx nginx -t 2>&1",
                capture_output=True,
            )
            docker.ssh.disconnect()
        
        if exit_code == 0:
            print_success("✓ Nginx SSL configuration is valid")
        else:
            print_error(f"Nginx SSL configuration error:\n{stderr}")
            sys.exit(1)
        
        # Test HTTPS endpoint
        with spinner("Testing HTTPS endpoint..."):
            docker.ssh.connect()
            exit_code_https, stdout_https, _ = docker.ssh.execute(
                f"curl -k -s -o /dev/null -w '%{{http_code}}' https://localhost/health || echo '000'",
                check=False,
                capture_output=True,
            )
            docker.ssh.disconnect()
        
        if stdout_https.strip() in ["200", "302"]:
            print_success(f"✓ HTTPS endpoint responding (HTTP {stdout_https.strip()})")
        else:
            print_warning(f"HTTPS endpoint test returned: {stdout_https.strip()}")
            print_warning("This might be normal if nginx is restarting")
        
    else:
        print_error(f"✗ {message}")
        print_section("Next Steps")
        print("To set up SSL certificates:")
        print("1. Obtain Cloudflare Origin Certificate from dashboard")
        print("2. Run: basec ssl setup edge")
        print("3. Or manually place certificates in nginx/ssl/ directory")
        sys.exit(1)


@app.command()
def setup(
    droplet: str = typer.Argument("edge", help="Droplet name (default: edge)"),
    cert_file: Optional[Path] = typer.Option(None, "--cert", "-c", help="Path to certificate file (origin.pem)"),
    key_file: Optional[Path] = typer.Option(None, "--key", "-k", help="Path to private key file (origin.key)"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode (prompt for certificate content)"),
) -> None:
    """Set up SSL certificates on edge droplet.
    
    This command helps you set up Cloudflare Origin Certificates on the edge droplet.
    You can provide certificate files or enter them interactively.
    """
    print_header("SSL Certificate Setup")
    
    droplet_config = get_droplet(droplet)
    if not droplet_config:
        print_error(f"Droplet '{droplet}' not found")
        sys.exit(1)
    
    if droplet_config.role != "edge":
        print_error(f"Droplet '{droplet}' is not an edge droplet. SSL is only needed for edge droplets.")
        sys.exit(1)
    
    docker = DockerCompose(droplet_config)
    remote_dir = docker.remote_dir
    ssl_dir = f"{remote_dir}/nginx/ssl"
    
    docker.ssh.connect()
    
    try:
        # Ensure SSL directory exists
        with spinner("Creating SSL directory..."):
            docker.ssh.execute(
                f"mkdir -p {shlex.quote(ssl_dir)}",
                check=True,
            )
        
        cert_content = None
        key_content = None
        
        # Try to find certificates in infra/ directory (auto-detect)
        infra_path = get_inventory_path().parent  # infra/ directory
        default_cert = infra_path / "origin.pem"
        default_key = infra_path / "origin.key"
        
        # Auto-detect if files exist in infra/ (unless explicitly provided)
        auto_detected = False
        if not cert_file and not key_file:
            if default_cert.exists() and default_key.exists():
                print_info(f"🔍 Auto-detected certificate files in {infra_path}")
                cert_file = default_cert
                key_file = default_key
                auto_detected = True
        
        # Get certificate content
        if cert_file and key_file:
            # Read from files
            if auto_detected:
                print_section("Reading auto-detected certificate files...")
            else:
                print_section("Reading certificate files...")
            try:
                with open(cert_file, "r") as f:
                    cert_content = f.read()
                with open(key_file, "r") as f:
                    key_content = f.read()
                print_success(f"✓ Read certificate from {cert_file}")
                print_success(f"✓ Read private key from {key_file}")
            except Exception as e:
                print_error(f"Failed to read certificate files: {e}")
                sys.exit(1)
        elif interactive:
            # Interactive mode
            print_section("Certificate Setup")
            print("To obtain Cloudflare Origin Certificate:")
            print("1. Go to: https://dash.cloudflare.com/")
            print("2. Select your domain: basecommerce.com.br")
            print("3. SSL/TLS → Origin Server → Create Certificate")
            print("4. Configure hostnames: *.basecommerce.com.br, basecommerce.com.br")
            print("5. Copy the Origin Certificate and Private Key")
            print()
            
            print("Paste the Origin Certificate (origin.pem):")
            print("(Press Ctrl+D (Linux/Mac) or Ctrl+Z+Enter (Windows) when finished)")
            print("Or enter 'DONE' on a new line when finished")
            cert_lines = []
            try:
                while True:
                    try:
                        line = input()
                        if line.strip() == "DONE":
                            break
                        cert_lines.append(line)
                    except EOFError:
                        break
            except KeyboardInterrupt:
                print_error("\nAborted by user")
                sys.exit(1)
            cert_content = "\n".join(cert_lines)
            
            if not cert_content.strip():
                print_error("No certificate content provided")
                sys.exit(1)
            
            print()
            print("Paste the Private Key (origin.key):")
            print("(Press Ctrl+D (Linux/Mac) or Ctrl+Z+Enter (Windows) when finished)")
            print("Or enter 'DONE' on a new line when finished")
            key_lines = []
            try:
                while True:
                    try:
                        line = input()
                        if line.strip() == "DONE":
                            break
                        key_lines.append(line)
                    except EOFError:
                        break
            except KeyboardInterrupt:
                print_error("\nAborted by user")
                sys.exit(1)
            key_content = "\n".join(key_lines)
        else:
            print_error("Could not find certificate files")
            print_info(f"Expected location: {default_cert} and {default_key}")
            print_info("Options:")
            print_info("  1. Place certificate files in infra/origin.pem and infra/origin.key")
            print_info("  2. Use --cert and --key options to specify file paths")
            print_info("  3. Use --interactive mode to paste certificates")
            sys.exit(1)
        
        # Validate certificate content
        if not cert_content.strip() or not cert_content.strip().startswith("-----BEGIN CERTIFICATE-----"):
            print_error("Invalid certificate content. Must start with '-----BEGIN CERTIFICATE-----'")
            sys.exit(1)
        
        if not key_content.strip() or not key_content.strip().startswith("-----BEGIN"):
            print_error("Invalid private key content. Must start with '-----BEGIN'")
            sys.exit(1)
        
        # Upload certificate
        with spinner("Uploading certificate files..."):
            cert_path = f"{ssl_dir}/origin.pem"
            key_path = f"{ssl_dir}/origin.key"
            
            # Write certificate to temp files
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
                f.write(cert_content)
                local_cert = f.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as f:
                f.write(key_content)
                local_key = f.name
            
            try:
                # Upload files to server
                docker.ssh.upload_file(Path(local_cert), cert_path)
                docker.ssh.upload_file(Path(local_key), key_path)
                
                # Set permissions
                docker.ssh.execute(
                    f"chmod 644 {shlex.quote(cert_path)} && chmod 600 {shlex.quote(key_path)}",
                    check=True,
                )
                
                print_success("✓ Certificate files uploaded")
            finally:
                # Cleanup temp files
                os.unlink(local_cert)
                os.unlink(local_key)
        
        # Validate certificates
        with spinner("Validating certificates..."):
            is_valid, message = validate_certificates(docker)
            if not is_valid:
                print_error(f"Certificate validation failed: {message}")
                sys.exit(1)
            print_success(f"✓ {message}")
        
        # Test nginx configuration
        with spinner("Testing nginx configuration..."):
            exit_code, stdout, stderr = docker._run_compose(
                "exec -T nginx nginx -t 2>&1",
                capture_output=True,
            )
            
            if exit_code != 0:
                print_error(f"Nginx configuration test failed:\n{stderr}")
                print_warning("Certificates were uploaded but nginx configuration has errors")
                sys.exit(1)
            
            print_success("✓ Nginx configuration is valid")
        
        # Restart nginx
        print_section("Restarting nginx...")
        with spinner("Restarting nginx container..."):
            docker._run_compose("restart nginx", capture_output=False)
        
        print_success("✓ Nginx restarted with SSL configuration")
        
        # Final check
        print_section("Final Verification")
        with spinner("Testing HTTPS endpoint..."):
            import time
            time.sleep(2)  # Wait for nginx to start
            
            exit_code_https, stdout_https, _ = docker.ssh.execute(
                f"curl -k -s -o /dev/null -w '%{{http_code}}' https://localhost/health || echo '000'",
                check=False,
                capture_output=True,
            )
        
        if stdout_https.strip() in ["200", "302"]:
            print_success(f"✓ HTTPS is working! (HTTP {stdout_https.strip()})")
        else:
            print_warning(f"HTTPS test returned: {stdout_https.strip()}")
            print_warning("This might be normal if nginx is still starting")
        
        print_section("Next Steps")
        print("1. Configure Cloudflare SSL mode to 'Full (strict)'")
        print("2. Test your domain: https://test.basecommerce.com.br")
        print("3. Verify SSL is working in browser")
        
    finally:
        docker.ssh.disconnect()


@app.command()
def test(
    droplet: str = typer.Argument("edge", help="Droplet name (default: edge)"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain to test (default: test.basecommerce.com.br)"),
) -> None:
    """Test SSL/HTTPS configuration."""
    print_header("SSL Test")
    
    droplet_config = get_droplet(droplet)
    if not droplet_config:
        print_error(f"Droplet '{droplet}' not found")
        sys.exit(1)
    
    test_domain = domain or "test.basecommerce.com.br"
    
    docker = DockerCompose(droplet_config)
    docker.ssh.connect()
    
    try:
        # Test internal HTTPS
        print_section("Testing Internal HTTPS")
        with spinner("Testing localhost HTTPS..."):
            exit_code, stdout, _ = docker.ssh.execute(
                f"curl -k -s -o /dev/null -w 'HTTP %{{http_code}}' https://localhost/health || echo 'FAILED'",
                check=False,
                capture_output=True,
            )
            print(f"Local HTTPS: {stdout.strip()}")
        
        # Test via domain (if accessible)
        print_section(f"Testing {test_domain}")
        with spinner(f"Testing https://{test_domain}..."):
            import subprocess
            try:
                result = subprocess.run(
                    ["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"https://{test_domain}/health"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                print(f"Domain HTTPS: HTTP {result.stdout.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print_warning(f"Could not test {test_domain} (curl not available or timeout)")
        
        # Check certificate info
        print_section("Certificate Information")
        with spinner("Getting certificate details..."):
            exit_code_info, stdout_info, _ = docker.ssh.execute(
                f"openssl x509 -in {docker.remote_dir}/nginx/ssl/origin.pem -noout -subject -issuer -dates 2>/dev/null || echo 'FAILED'",
                check=False,
                capture_output=True,
            )
            if "FAILED" not in stdout_info:
                print(stdout_info)
            else:
                print_warning("Could not read certificate details")
        
    finally:
        docker.ssh.disconnect()


if __name__ == "__main__":
    app()

