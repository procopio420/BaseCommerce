"""Deploy command - deploy services to droplets."""

import os
import shlex
import sys
from pathlib import Path
from typing import Optional

import typer

from basec.docker import DockerCompose
from basec.envs import get_edge_path, get_env_path
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
    print_warning,
    spinner,
)

app = typer.Typer()


def deploy_droplet(name: str, config, env: str = "production", tag: Optional[str] = None) -> int:
    """Deploy services to a single droplet.
    
    Args:
        name: Droplet name
        config: Droplet configuration
        env: Environment name
        tag: Optional image tag to deploy (e.g., 'sha-abc123'). If provided, 
             generates docker-compose.override.yml with image tags.
    """
    print_section(f"Deploying: {name} ({config.ip})")
    
    try:
        docker = DockerCompose(config)
        
        # Sync files if git is available (pull latest changes)
        try:
            remote_dir = docker.remote_dir
            exit_code, stdout, stderr = docker.ssh.execute(
                f"cd {shlex.quote(remote_dir)} && git rev-parse --git-dir > /dev/null 2>&1 && git pull || exit 0",
                check=False,
                capture_output=True,
            )
            if exit_code == 0 and ("Updating" in stdout or "Fast-forward" in stdout or "Merge made" in stdout):
                print_success("✓ Pulled latest changes from git")
        except Exception:
            # Git not available or not a git repo - that's OK, try file sync or continue
            pass
        
        # For edge role, sync critical nginx configuration files and verify setup
        if config.role == "edge":
            try:
                remote_dir = docker.remote_dir
                local_edge_path = get_edge_path(env)
                from basec.envs import get_project_root
                project_root = get_project_root()
                
                docker.ssh.connect()
                
                # Always sync docker-compose.yml
                with spinner("Syncing docker-compose.yml..."):
                    docker_compose_remote = f"{remote_dir}/docker-compose.yml"
                    docker.ssh.upload_file(local_edge_path / "docker-compose.yml", docker_compose_remote)
                    print_success("✓ Synced docker-compose.yml")
                
                # Check if we need to sync files (detect old config with conf.d mount or missing templates)
                exit_code1, stdout1, _ = docker.ssh.execute(
                    f"cd {shlex.quote(remote_dir)} && (grep -q 'nginx/conf.d:/etc/nginx/conf.d' docker-compose.yml 2>/dev/null || ! test -f nginx/templates/default.conf.template) && echo 'NEEDS_SYNC' || echo 'OK'",
                    check=False,
                    capture_output=True,
                )
                
                if "NEEDS_SYNC" in stdout1:
                    # Server has old config or missing template, sync critical files
                    with spinner("Syncing nginx configuration files..."):
                        # Upload nginx templates directory
                        templates_local = local_edge_path / "nginx" / "templates" / "default.conf.template"
                        if templates_local.exists():
                            # Ensure remote templates directory exists
                            docker.ssh.execute(
                                f"mkdir -p {shlex.quote(remote_dir)}/nginx/templates",
                                check=False,
                                capture_output=True,
                            )
                            templates_remote = f"{remote_dir}/nginx/templates/default.conf.template"
                            docker.ssh.upload_file(templates_local, templates_remote)
                        
                        print_success("✓ Synced nginx configuration files")
                
                # Sync source code needed for building auth service
                with spinner("Syncing source code for auth build..."):
                    try:
                        # Sync basecore package (needed by auth Dockerfile)
                        basecore_local = project_root / "packages" / "basecore"
                        if basecore_local.exists():
                            docker.ssh.upload_directory(
                                basecore_local,
                                f"{remote_dir}/packages/basecore"
                            )
                            print_success("✓ Synced basecore package")
                        
                        # Sync auth service source code
                        auth_src_local = project_root / "apps" / "auth" / "src"
                        if auth_src_local.exists():
                            docker.ssh.upload_directory(
                                auth_src_local,
                                f"{remote_dir}/apps/auth/src"
                            )
                            print_success("✓ Synced auth source code")
                        
                        # Sync auth Dockerfile
                        auth_dockerfile_local = project_root / "apps" / "auth" / "Dockerfile"
                        if auth_dockerfile_local.exists():
                            docker.ssh.execute(
                                f"mkdir -p {shlex.quote(remote_dir)}/apps/auth",
                                check=False,
                            )
                            docker.ssh.upload_file(
                                auth_dockerfile_local,
                                f"{remote_dir}/apps/auth/Dockerfile"
                            )
                            print_success("✓ Synced auth Dockerfile")
                        
                    except Exception as e:
                        print_warning(f"⚠ Failed to sync source code: {e}")
                
                # Verify VERTICAL_HOST is set in .env
                exit_code2, stdout2, _ = docker.ssh.execute(
                    f"cd {shlex.quote(remote_dir)} && test -f .env && grep -q '^VERTICAL_HOST=' .env 2>/dev/null && echo 'VERTICAL_HOST_SET' || echo 'VERTICAL_HOST_MISSING'",
                    check=False,
                    capture_output=True,
                )
                
                if "VERTICAL_HOST_MISSING" in stdout2:
                    print_error("⚠ WARNING: VERTICAL_HOST not set in .env file on server")
                    print_error("  Please ensure .env file has: VERTICAL_HOST=191.252.120.176")
                
                docker.ssh.disconnect()
            except Exception as e:
                # File sync/verification failed - continue anyway, might work with git or manual setup
                print_warning(f"⚠ File sync failed: {e}")
                pass
        
        # Set image tags if provided
        if tag:
            with spinner(f"Setting image tag: {tag}..."):
                docker.set_image_tags(tag)
        
        # For edge role with auth service, rebuild to pick up code changes
        if config.role == "edge":
            try:
                with spinner("Rebuilding auth service (no cache)..."):
                    docker._run_compose("build --no-cache auth", capture_output=False)
            except Exception:
                # Build failed - continue anyway, might use cached image
                pass
            
            # Check SSL certificates (warn if missing, but don't fail deploy)
            try:
                from basec.ssl import validate_certificates
                docker.ssh.connect()
                is_valid, message = validate_certificates(docker)
                docker.ssh.disconnect()
                
                if not is_valid:
                    print_warning(f"SSL certificates not configured: {message}")
                    print_warning("  Run 'basec ssl setup edge' to configure SSL certificates")
                    print_warning("  Or set up manually following SETUP_SSL.md")
                else:
                    print_success(f"✓ {message}")
            except Exception as e:
                # SSL check failed - continue deploy anyway
                print_warning(f"Could not verify SSL certificates: {e}")
        
        with spinner("Starting services..."):
            docker.up(detach=True, pull=False, remove_orphans=True)
        
        # Save to deployment history if tag provided
        if tag:
            try:
                from basec.rollback import save_deploy_history
                save_deploy_history(docker, tag)
            except ImportError:
                # Rollback module might not be available in all versions
                pass
        
        print_success(f"Deploy complete for {name}")
        return 0
    except Exception as e:
        print_error(f"Deploy failed for {name}: {e}")
        return 1


@app.command()
def deploy(
    target: str = typer.Argument(
        ...,
        help="Target to deploy: 'edge', 'platform', 'vertical <name>', or 'all'",
    ),
    vertical_name: str = typer.Option(
        None,
        "--vertical",
        "-v",
        help="Vertical name (required if target is 'vertical')",
    ),
    env: str = typer.Option(
        "production",
        "--env",
        "-e",
        help="Environment name (default: production)",
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Image tag to deploy (e.g., 'sha-abc123' or 'latest-staging'). "
             "If provided, generates docker-compose.override.yml with image tags.",
    ),
) -> None:
    """Deploy services to droplets."""
    # Validate environment path exists
    from basec.envs import validate_env_path
    
    if not validate_env_path(env):
        print_error(f"Environment '{env}' not found. Available environments: production, development")
        sys.exit(1)
    
    env_tag_info = f" (env: {env}"
    if tag:
        env_tag_info += f", tag: {tag}"
    env_tag_info += ")"
    print_header(f"BaseCommerce Deploy{env_tag_info}")
    
    total_failed = 0
    
    if target == "all":
        # Deploy all droplets in order: platform, edge, verticals
        droplets = list_droplets(env)
        
        # Platform first
        platform_droplets = {k: v for k, v in droplets.items() if v.role == "platform"}
        for name, config in platform_droplets.items():
            total_failed += deploy_droplet(name, config, env, tag)
        
        # Edge second
        edge_droplets = {k: v for k, v in droplets.items() if v.role == "edge"}
        for name, config in edge_droplets.items():
            total_failed += deploy_droplet(name, config, env, tag)
        
        # Verticals last
        vertical_droplets = {k: v for k, v in droplets.items() if v.role == "vertical"}
        for name, config in vertical_droplets.items():
            total_failed += deploy_droplet(name, config, env, tag)
    
    elif target == "edge":
        edge_droplets = get_droplets_by_role("edge", env)
        if not edge_droplets:
            print_error("No edge droplets found")
            sys.exit(1)
        for name, config in edge_droplets.items():
            total_failed += deploy_droplet(name, config, env, tag)
    
    elif target == "platform":
        platform_droplets = get_droplets_by_role("platform", env)
        if not platform_droplets:
            print_error("No platform droplets found")
            sys.exit(1)
        for name, config in platform_droplets.items():
            total_failed += deploy_droplet(name, config, env, tag)
    
    elif target == "vertical":
        if not vertical_name:
            print_error("Vertical name required (use --vertical <name>)")
            sys.exit(1)
        droplet = get_droplet(f"vertical_{vertical_name}", env)
        if not droplet:
            print_error(f"Vertical droplet 'vertical_{vertical_name}' not found")
            sys.exit(1)
        total_failed += deploy_droplet(f"vertical_{vertical_name}", droplet, env, tag)
    
    else:
        # Try to find droplet by name
        droplet = get_droplet(target, env)
        if not droplet:
            print_error(f"Droplet '{target}' not found")
            sys.exit(1)
        total_failed += deploy_droplet(target, droplet, env, tag)
    
    print()
    if total_failed == 0:
        print_success("All deploys completed successfully")
        sys.exit(0)
    else:
        print_error("Some deploys failed")
        sys.exit(1)

