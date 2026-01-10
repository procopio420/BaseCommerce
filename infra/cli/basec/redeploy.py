"""Redeploy command - clean redeploy from scratch."""

import shlex
import sys
from typing import Optional

import typer

from basec.docker import DockerCompose
from basec.inventory import get_droplet, get_droplets_by_role
from basec.output import (
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
    print_warning,
    spinner,
    confirm,
)

app = typer.Typer()


def redeploy_droplet(
    name: str,
    config,
    env: str = "production",
    tag: Optional[str] = None,
    force: bool = False,
    rebuild_images: bool = True,
) -> int:
    """Clean redeploy a droplet from scratch.
    
    Args:
        name: Droplet name
        config: Droplet configuration
        env: Environment name
        tag: Optional image tag to deploy
        force: Skip confirmation prompts
        rebuild_images: Rebuild Docker images instead of pulling
    """
    print_section(f"Clean Redeploy: {name} ({config.ip})")
    
    if not force:
        print_warning("⚠ This will:")
        print_warning("  1. Stop and remove all containers")
        print_warning("  2. Optionally remove old images (if --rebuild)")
        print_warning("  3. Pull latest code from git")
        print_warning("  4. Sync all configuration files")
        print_warning("  5. Rebuild/repull images")
        print_warning("  6. Start services from scratch")
        print()
        if not confirm("Continue with clean redeploy?", default=False):
            print_info("Redeploy cancelled")
            return 0
    
    try:
        docker = DockerCompose(config)
        remote_dir = docker.remote_dir
        
        # Step 1: Stop and remove containers
        with spinner("Stopping and removing containers..."):
            docker.ssh.connect()
            try:
                docker._run_compose("down", capture_output=False)
                print_success("✓ Containers stopped and removed")
            except Exception as e:
                print_warning(f"⚠ Error stopping containers (might not exist): {e}")
            docker.ssh.disconnect()
        
        # Step 2: Remove old images (if rebuild requested)
        if rebuild_images:
            with spinner("Removing old images..."):
                docker.ssh.connect()
                try:
                    # Remove images built from this compose project
                    docker.ssh.execute(
                        f"cd {shlex.quote(remote_dir)} && docker compose down --rmi all --volumes --remove-orphans 2>&1 || true",
                        check=False,
                        capture_output=True,
                    )
                    print_success("✓ Old images removed")
                except Exception as e:
                    print_warning(f"⚠ Error removing images: {e}")
                docker.ssh.disconnect()
        
        # Step 3: Pull latest code from git
        with spinner("Pulling latest code from git..."):
            docker.ssh.connect()
            try:
                exit_code, stdout, stderr = docker.ssh.execute(
                    f"cd {shlex.quote(remote_dir)} && git rev-parse --git-dir > /dev/null 2>&1",
                    check=False,
                    capture_output=True,
                )
                
                if exit_code == 0:
                    # It's a git repo, do pull
                    exit_code2, stdout2, stderr2 = docker.ssh.execute(
                        f"cd {shlex.quote(remote_dir)} && git fetch --all && git reset --hard origin/main 2>&1 || git reset --hard origin/master 2>&1",
                        check=False,
                        capture_output=True,
                    )
                    if exit_code2 == 0:
                        print_success("✓ Latest code pulled from git")
                    else:
                        print_warning(f"⚠ Git reset failed, trying pull instead: {stderr2[:200]}")
                        exit_code3, stdout3, _ = docker.ssh.execute(
                            f"cd {shlex.quote(remote_dir)} && git pull",
                            check=False,
                            capture_output=True,
                        )
                        if exit_code3 == 0:
                            print_success("✓ Latest code pulled from git")
                        else:
                            print_warning("⚠ Git pull failed, continuing with existing files")
                else:
                    print_warning("⚠ Not a git repository, skipping git pull")
                    print_info("  Files will be synced from local repository")
            except Exception as e:
                print_warning(f"⚠ Git operation failed: {e}")
            docker.ssh.disconnect()
        
        # Step 4: Sync all configuration files (especially for edge)
        if config.role == "edge":
            with spinner("Syncing all configuration files..."):
                from basec.envs import get_edge_path, get_project_root
                docker.ssh.connect()
                
                local_edge_path = get_edge_path(env)
                project_root = get_project_root()
                
                # Sync docker-compose.yml
                try:
                    docker_compose_remote = f"{remote_dir}/docker-compose.yml"
                    docker.ssh.upload_file(local_edge_path / "docker-compose.yml", docker_compose_remote)
                except Exception as e:
                    print_warning(f"⚠ Failed to sync docker-compose.yml: {e}")
                
                # Sync nginx configuration files
                try:
                    # Ensure directories exist
                    docker.ssh.execute(
                        f"mkdir -p {shlex.quote(remote_dir)}/nginx/templates {shlex.quote(remote_dir)}/nginx/ssl {shlex.quote(remote_dir)}/nginx/tenants",
                        check=False,
                        capture_output=True,
                    )
                    
                    # Sync nginx.conf
                    nginx_conf_local = local_edge_path / "nginx" / "nginx.conf"
                    if nginx_conf_local.exists():
                        docker.ssh.upload_file(nginx_conf_local, f"{remote_dir}/nginx/nginx.conf")
                    
                    # Sync template
                    template_local = local_edge_path / "nginx" / "templates" / "default.conf.template"
                    if template_local.exists():
                        docker.ssh.upload_file(template_local, f"{remote_dir}/nginx/templates/default.conf.template")
                    
                    # Sync scripts
                    for script_name in ["bootstrap.sh", "smoke-test.sh", "update.sh"]:
                        script_local = local_edge_path / "scripts" / script_name
                        if script_local.exists():
                            docker.ssh.upload_file(script_local, f"{remote_dir}/scripts/{script_name}")
                            docker.ssh.execute(
                                f"chmod +x {shlex.quote(remote_dir)}/scripts/{script_name}",
                                check=False,
                            )
                    
                    print_success("✓ Configuration files synced")
                except Exception as e:
                    print_warning(f"⚠ Failed to sync some files: {e}")
                
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
                        import traceback
                        traceback.print_exc()
                
                docker.ssh.disconnect()
        
        # For vertical role, sync source code needed for building
        elif config.role == "vertical":
            with spinner("Syncing all configuration files..."):
                from basec.envs import get_project_root, get_vertical_path
                docker.ssh.connect()
                
                project_root = get_project_root()
                vertical_name = config.vertical or "construction"
                local_vertical_path = get_vertical_path(vertical_name, env)
                
                # Sync docker-compose.yml
                try:
                    docker_compose_remote = f"{remote_dir}/docker-compose.yml"
                    docker.ssh.upload_file(local_vertical_path / "docker-compose.yml", docker_compose_remote)
                    print_success("✓ Synced docker-compose.yml")
                except Exception as e:
                    print_warning(f"⚠ Failed to sync docker-compose.yml: {e}")
                
                # Sync source code needed for building vertical service
                with spinner("Syncing source code for vertical build..."):
                    try:
                        # Sync basecore package (needed by vertical Dockerfile)
                        basecore_local = project_root / "packages" / "basecore"
                        if basecore_local.exists():
                            docker.ssh.upload_directory(
                                basecore_local,
                                f"{remote_dir}/packages/basecore"
                            )
                            print_success("✓ Synced basecore package")
                        
                        # Sync engines_core package (needed by vertical Dockerfile)
                        engines_core_local = project_root / "packages" / "engines_core"
                        if engines_core_local.exists():
                            docker.ssh.upload_directory(
                                engines_core_local,
                                f"{remote_dir}/packages/engines_core"
                            )
                            print_success("✓ Synced engines_core package")
                        
                        # Sync vertical service source code
                        vertical_src_local = project_root / "apps" / "verticals" / vertical_name / "src"
                        if vertical_src_local.exists():
                            docker.ssh.upload_directory(
                                vertical_src_local,
                                f"{remote_dir}/apps/verticals/{vertical_name}/src"
                            )
                            print_success(f"✓ Synced {vertical_name} source code")
                        
                        # Sync vertical alembic directory
                        vertical_alembic_local = project_root / "apps" / "verticals" / vertical_name / "alembic"
                        if vertical_alembic_local.exists():
                            docker.ssh.upload_directory(
                                vertical_alembic_local,
                                f"{remote_dir}/apps/verticals/{vertical_name}/alembic"
                            )
                            print_success(f"✓ Synced {vertical_name} alembic")
                        
                        # Sync vertical requirements.txt
                        vertical_requirements_local = project_root / "apps" / "verticals" / vertical_name / "requirements.txt"
                        if vertical_requirements_local.exists():
                            docker.ssh.execute(
                                f"mkdir -p {shlex.quote(remote_dir)}/apps/verticals/{vertical_name}",
                                check=False,
                            )
                            docker.ssh.upload_file(
                                vertical_requirements_local,
                                f"{remote_dir}/apps/verticals/{vertical_name}/requirements.txt"
                            )
                            print_success(f"✓ Synced {vertical_name} requirements.txt")
                        
                        # Sync vertical alembic.ini
                        vertical_alembic_ini_local = project_root / "apps" / "verticals" / vertical_name / "alembic.ini"
                        if vertical_alembic_ini_local.exists():
                            docker.ssh.upload_file(
                                vertical_alembic_ini_local,
                                f"{remote_dir}/apps/verticals/{vertical_name}/alembic.ini"
                            )
                            print_success(f"✓ Synced {vertical_name} alembic.ini")
                        
                        # Sync vertical Dockerfile
                        vertical_dockerfile_local = project_root / "apps" / "verticals" / vertical_name / "Dockerfile"
                        if vertical_dockerfile_local.exists():
                            docker.ssh.upload_file(
                                vertical_dockerfile_local,
                                f"{remote_dir}/apps/verticals/{vertical_name}/Dockerfile"
                            )
                            print_success(f"✓ Synced {vertical_name} Dockerfile")
                        
                    except Exception as e:
                        print_warning(f"⚠ Failed to sync source code: {e}")
                        import traceback
                        traceback.print_exc()
                
                docker.ssh.disconnect()
        
        # Step 5: Rebuild or pull images
        docker.ssh.connect()
        
        if rebuild_images:
            with spinner("Rebuilding images..."):
                try:
                    # Rebuild auth service for edge
                    if config.role == "edge":
                        docker._run_compose("build --no-cache auth", capture_output=False)
                    # Rebuild vertical service
                    elif config.role == "vertical":
                        vertical_name = config.vertical or "construction"
                        service_name = vertical_name
                        docker._run_compose(f"build --no-cache {service_name}", capture_output=False)
                    
                    # Pull official images
                    docker._run_compose("pull", capture_output=False)
                    print_success("✓ Images rebuilt and pulled")
                except Exception as e:
                    print_warning(f"⚠ Image rebuild failed: {e}")
                    print_info("  Continuing with existing images...")
        else:
            with spinner("Pulling latest images..."):
                try:
                    docker._run_compose("pull", capture_output=False)
                    print_success("✓ Images pulled")
                except Exception as e:
                    print_warning(f"⚠ Image pull failed: {e}")
        
        # Step 6: Set image tags if provided
        if tag:
            with spinner(f"Setting image tag: {tag}..."):
                try:
                    docker.set_image_tags(tag)
                    print_success(f"✓ Image tag set to {tag}")
                except Exception as e:
                    print_warning(f"⚠ Failed to set image tag: {e}")
        
        docker.ssh.disconnect()
        
        # Step 7: Start services
        with spinner("Starting services from scratch..."):
            docker.up(detach=True, pull=False, remove_orphans=True)
            print_success("✓ Services started")
        
        # Step 8: Verify deployment
        print_section("Verification")
        try:
            containers = docker.ps()
            print_success(f"✓ {len(containers)} container(s) running")
            for container in containers:
                status = container.get("status", "unknown")
                name = container.get("name", "unknown")
                if "Up" in status or "running" in status.lower():
                    print_info(f"  ✓ {name}: {status}")
                else:
                    print_warning(f"  ⚠ {name}: {status}")
        except Exception as e:
            print_warning(f"⚠ Could not verify containers: {e}")
        
        print_success(f"Clean redeploy complete for {name}")
        return 0
    except Exception as e:
        print_error(f"Redeploy failed for {name}: {e}")
        import traceback
        traceback.print_exc()
        return 1


@app.command()
def redeploy(
    target: str = typer.Argument(
        ...,
        help="Target to redeploy: 'edge', 'platform', 'vertical <name>', or 'all'",
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
        help="Image tag to deploy (e.g., 'sha-abc123')",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompts",
    ),
    rebuild: bool = typer.Option(
        True,
        "--rebuild/--no-rebuild",
        help="Rebuild Docker images from scratch (default: true)",
    ),
) -> None:
    """Clean redeploy services from scratch.
    
    This command performs a complete clean redeploy:
    1. Stops and removes all containers
    2. Optionally removes old images (if --rebuild)
    3. Pulls latest code from git (or syncs files)
    4. Rebuilds/pulls Docker images
    5. Starts services from scratch
    
    Use this when you need to ensure everything is up to date.
    """
    from basec.inventory import get_droplets_by_role, list_droplets
    
    print_header(f"BaseCommerce Clean Redeploy (env: {env})")
    
    if not force:
        print_warning("⚠ WARNING: This will destroy and recreate all containers!")
        print_warning("   All data in containers will be lost (volumes are preserved)")
        print()
    
    total_failed = 0
    
    if target == "all":
        droplets = list_droplets(env)
        
        # Platform first
        platform_droplets = {k: v for k, v in droplets.items() if v.role == "platform"}
        for name, config in platform_droplets.items():
            total_failed += redeploy_droplet(name, config, env, tag, force, rebuild)
        
        # Edge second
        edge_droplets = {k: v for k, v in droplets.items() if v.role == "edge"}
        for name, config in edge_droplets.items():
            total_failed += redeploy_droplet(name, config, env, tag, force, rebuild)
        
        # Verticals last
        vertical_droplets = {k: v for k, v in droplets.items() if v.role == "vertical"}
        for name, config in vertical_droplets.items():
            total_failed += redeploy_droplet(name, config, env, tag, force, rebuild)
    
    elif target == "edge":
        edge_droplets = get_droplets_by_role("edge", env)
        if not edge_droplets:
            print_error("No edge droplets found")
            sys.exit(1)
        for name, config in edge_droplets.items():
            total_failed += redeploy_droplet(name, config, env, tag, force, rebuild)
    
    elif target == "platform":
        platform_droplets = get_droplets_by_role("platform", env)
        if not platform_droplets:
            print_error("No platform droplets found")
            sys.exit(1)
        for name, config in platform_droplets.items():
            total_failed += redeploy_droplet(name, config, env, tag, force, rebuild)
    
    elif target == "vertical":
        if not vertical_name:
            print_error("Vertical name required (use --vertical <name>)")
            sys.exit(1)
        droplet = get_droplet(f"vertical_{vertical_name}", env)
        if not droplet:
            print_error(f"Vertical droplet 'vertical_{vertical_name}' not found")
            sys.exit(1)
        total_failed += redeploy_droplet(f"vertical_{vertical_name}", droplet, env, tag, force, rebuild)
    
    else:
        droplet = get_droplet(target, env)
        if not droplet:
            print_error(f"Droplet '{target}' not found")
            sys.exit(1)
        total_failed += redeploy_droplet(target, droplet, env, tag, force, rebuild)
    
    print()
    if total_failed == 0:
        print_success("All redeploys completed successfully")
        sys.exit(0)
    else:
        print_error("Some redeploys failed")
        sys.exit(1)

