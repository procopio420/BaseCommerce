"""
WhatsApp CLI

Command-line interface for WhatsApp Messaging Engine administration.

Commands:
- bind-tenant: Register a tenant's WhatsApp number
- unbind-tenant: Remove a tenant's WhatsApp binding
- send-test: Send a test message
- list-conversations: List conversations for a tenant
- replay-dlq: Replay messages from dead letter queue
"""

import asyncio
import os
from typing import Optional
from uuid import UUID

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="whatsapp-cli",
    help="WhatsApp Messaging Engine CLI",
)

console = Console()


def get_db():
    """Get database session."""
    from basecore.db import get_db as _get_db
    return next(_get_db())


def get_redis():
    """Get Redis client."""
    from basecore.redis import get_redis_client
    return get_redis_client()


@app.command()
def bind_tenant(
    tenant_id: str = typer.Argument(..., help="Tenant UUID"),
    phone_number_id: Optional[str] = typer.Option(None, help="WhatsApp phone number ID (Meta)"),
    waba_id: Optional[str] = typer.Option(None, help="WhatsApp Business Account ID (Meta)"),
    display_number: str = typer.Argument(..., help="Display phone number (e.g., +5511999999999)"),
    provider: str = typer.Option("meta", help="Provider (meta, evolution, or stub)"),
    access_token: Optional[str] = typer.Option(None, help="Access token (Meta, will be encrypted)"),
    verify_token: Optional[str] = typer.Option(None, help="Webhook verify token (Meta)"),
    instance_name: Optional[str] = typer.Option(None, help="Evolution instance name"),
    api_url: Optional[str] = typer.Option(None, help="Evolution API base URL"),
    api_key: Optional[str] = typer.Option(None, help="Evolution API key (will be encrypted)"),
):
    """
    Register a tenant's WhatsApp Business number.

    This creates a binding between a tenant and a WhatsApp Business phone number.
    The phone_number_id is used to route incoming webhooks to the correct tenant.
    """
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        rprint(f"[red]Invalid tenant ID: {tenant_id}[/red]")
        raise typer.Exit(1)

    db = get_db()

    try:
        from messaging_whatsapp.persistence.repo import WhatsAppRepository

        repo = WhatsAppRepository(db)

        # Validate provider-specific fields
        if provider == "meta":
            if not phone_number_id or not waba_id:
                rprint("[red]Meta provider requires phone_number_id and waba_id[/red]")
                raise typer.Exit(1)
            # Check if binding already exists
            existing = repo.get_binding_by_phone_number_id(phone_number_id)
            if existing:
                rprint(f"[yellow]Binding already exists for phone_number_id: {phone_number_id}[/yellow]")
                rprint(f"  Tenant: {existing.tenant_id}")
                rprint(f"  Active: {existing.is_active}")
                raise typer.Exit(1)
        elif provider == "evolution":
            if not instance_name or not api_url or not api_key:
                rprint("[red]Evolution provider requires instance_name, api_url, and api_key[/red]")
                raise typer.Exit(1)
            # Check if binding already exists
            existing = repo.get_binding_by_instance_name(instance_name)
            if existing:
                rprint(f"[yellow]Binding already exists for instance_name: {instance_name}[/yellow]")
                rprint(f"  Tenant: {existing.tenant_id}")
                rprint(f"  Active: {existing.is_active}")
                raise typer.Exit(1)

        # Encrypt access token if provided
        encrypted_token = None
        if access_token:
            encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
            if encryption_key:
                from cryptography.fernet import Fernet
                f = Fernet(encryption_key.encode())
                encrypted_token = f.encrypt(access_token.encode()).decode()
            else:
                # Store unencrypted (for development)
                encrypted_token = access_token
                rprint("[yellow]Warning: WHATSAPP_ENCRYPTION_KEY not set, storing token unencrypted[/yellow]")

        # Encrypt API key for Evolution
        encrypted_api_key = None
        if provider == "evolution" and api_key:
            encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
            if encryption_key:
                from cryptography.fernet import Fernet
                f = Fernet(encryption_key.encode())
                encrypted_api_key = f.encrypt(api_key.encode()).decode()
            else:
                encrypted_api_key = api_key
                rprint("[yellow]Warning: WHATSAPP_ENCRYPTION_KEY not set, storing API key unencrypted[/yellow]")

        # Create binding
        binding = WhatsAppTenantBinding(
            tenant_id=tenant_uuid,
            provider=provider,
            phone_number_id=phone_number_id,
            waba_id=waba_id,
            display_number=display_number,
            access_token_encrypted=encrypted_token,
            webhook_verify_token=verify_token,
            instance_name=instance_name,
            api_url=api_url,
            api_key=encrypted_api_key,
        )
        db.add(binding)

        db.commit()

        rprint(f"[green]Successfully created binding:[/green]")
        rprint(f"  ID: {binding.id}")
        rprint(f"  Tenant: {binding.tenant_id}")
        rprint(f"  Provider: {binding.provider}")
        rprint(f"  Display: {binding.display_number}")
        if provider == "meta":
            rprint(f"  Phone Number ID: {binding.phone_number_id}")
            rprint(f"  WABA ID: {binding.waba_id}")
        elif provider == "evolution":
            rprint(f"  Instance Name: {binding.instance_name}")
            rprint(f"  API URL: {binding.api_url}")

    finally:
        db.close()


@app.command()
def unbind_tenant(
    phone_number_id: str = typer.Argument(..., help="WhatsApp phone number ID to unbind"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deactivation"),
):
    """
    Deactivate a tenant's WhatsApp binding.

    This marks the binding as inactive. The binding is not deleted for audit purposes.
    """
    db = get_db()

    try:
        from messaging_whatsapp.persistence.repo import WhatsAppRepository

        repo = WhatsAppRepository(db)
        binding = repo.get_binding_by_phone_number_id(phone_number_id)

        if not binding:
            rprint(f"[red]No binding found for phone_number_id: {phone_number_id}[/red]")
            raise typer.Exit(1)

        if not binding.is_active:
            rprint(f"[yellow]Binding is already inactive[/yellow]")
            raise typer.Exit(0)

        if not force:
            confirm = typer.confirm(
                f"Deactivate binding for tenant {binding.tenant_id}?"
            )
            if not confirm:
                rprint("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        binding.is_active = False
        db.commit()

        rprint(f"[green]Binding deactivated successfully[/green]")

    finally:
        db.close()


@app.command()
def send_test(
    to: str = typer.Argument(..., help="Recipient phone number (E.164 format)"),
    text: str = typer.Option("Hello from BaseCommerce!", help="Message text"),
    tenant_id: Optional[str] = typer.Option(None, help="Tenant UUID (uses first active binding if not specified)"),
):
    """
    Send a test message.

    This sends a message directly via the provider for testing purposes.
    """
    db = get_db()

    try:
        from messaging_whatsapp.persistence.repo import WhatsAppRepository
        from messaging_whatsapp.routing.tenant_resolver import TenantResolver

        repo = WhatsAppRepository(db)
        resolver = TenantResolver(db)

        # Get binding
        if tenant_id:
            binding = resolver.get_binding_for_tenant(UUID(tenant_id))
        else:
            # Get first active binding (for testing)
            from sqlalchemy import text
            result = db.execute(
                text("SELECT phone_number_id FROM whatsapp_tenant_bindings WHERE is_active = true LIMIT 1")
            )
            row = result.fetchone()
            if row:
                binding = repo.get_binding_by_phone_number_id(row[0])
            else:
                binding = None

        if not binding:
            rprint("[red]No active binding found[/red]")
            raise typer.Exit(1)

        # Get access token
        access_token = resolver.get_access_token(
            binding,
            os.getenv("WHATSAPP_ENCRYPTION_KEY"),
        )

        if not access_token:
            rprint("[red]No access token configured for this binding[/red]")
            raise typer.Exit(1)

        # Send message
        provider_type = os.getenv("WHATSAPP_PROVIDER", "stub")

        async def send():
            if provider_type == "meta":
                from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
                provider = MetaCloudWhatsAppProvider()
            else:
                from messaging_whatsapp.providers.stub import StubWhatsAppProvider
                provider = StubWhatsAppProvider()

            response = await provider.send_text(
                phone_number_id=binding.phone_number_id,
                access_token=access_token,
                to=to,
                text=text,
            )

            if hasattr(provider, "close"):
                await provider.close()

            return response

        response = asyncio.run(send())

        if response.success:
            rprint(f"[green]Message sent successfully![/green]")
            rprint(f"  Message ID: {response.message_id}")
        else:
            rprint(f"[red]Failed to send message[/red]")
            rprint(f"  Error: {response.error_message}")
            rprint(f"  Code: {response.error_code}")

    finally:
        db.close()


@app.command()
def list_conversations(
    tenant_id: str = typer.Argument(..., help="Tenant UUID"),
    status: Optional[str] = typer.Option(None, help="Filter by status (active, closed, etc)"),
    limit: int = typer.Option(20, help="Maximum number of conversations to show"),
):
    """
    List conversations for a tenant.
    """
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        rprint(f"[red]Invalid tenant ID: {tenant_id}[/red]")
        raise typer.Exit(1)

    db = get_db()

    try:
        from messaging_whatsapp.persistence.models import ConversationStatus
        from messaging_whatsapp.persistence.repo import WhatsAppRepository

        repo = WhatsAppRepository(db)

        status_filter = None
        if status:
            try:
                status_filter = ConversationStatus(status)
            except ValueError:
                rprint(f"[yellow]Unknown status: {status}[/yellow]")

        conversations = repo.list_conversations(
            tenant_id=tenant_uuid,
            status=status_filter,
            limit=limit,
        )

        if not conversations:
            rprint("[yellow]No conversations found[/yellow]")
            raise typer.Exit(0)

        table = Table(title=f"Conversations for tenant {tenant_id[:8]}...")
        table.add_column("ID", style="dim")
        table.add_column("Phone")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Messages")
        table.add_column("Last Message")

        for conv in conversations:
            table.add_row(
                str(conv.id)[:8] + "...",
                conv.customer_phone,
                conv.customer_name or "-",
                conv.status,
                conv.message_count,
                conv.last_message_at.strftime("%Y-%m-%d %H:%M") if conv.last_message_at else "-",
            )

        console.print(table)

    finally:
        db.close()


@app.command()
def list_bindings(
    tenant_id: Optional[str] = typer.Option(None, help="Filter by tenant UUID"),
    all_: bool = typer.Option(False, "--all", "-a", help="Show inactive bindings too"),
):
    """
    List WhatsApp bindings.
    """
    db = get_db()

    try:
        from sqlalchemy import text

        query = "SELECT id, tenant_id, phone_number_id, waba_id, display_number, provider, instance_name, api_url, is_active, created_at FROM whatsapp_tenant_bindings"
        params = {}

        conditions = []
        if tenant_id:
            conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = UUID(tenant_id)
        if not all_:
            conditions.append("is_active = true")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        if not rows:
            rprint("[yellow]No bindings found[/yellow]")
            raise typer.Exit(0)

        table = Table(title="WhatsApp Bindings")
        table.add_column("Tenant", style="dim")
        table.add_column("Provider")
        table.add_column("Identifier", help="Phone Number ID (Meta) or Instance Name (Evolution)")
        table.add_column("Display")
        table.add_column("Active")

        for row in rows:
            identifier = row[2] if row[5] == "meta" else (row[6] or "-")
            table.add_row(
                str(row[1])[:8] + "...",
                row[5],
                identifier,
                row[4],
                "Yes" if row[8] else "No",
            )

        console.print(table)

    finally:
        db.close()


@app.command()
def replay_dlq(
    limit: int = typer.Option(10, help="Maximum messages to replay"),
    stream: str = typer.Option("bc:whatsapp:dlq", help="DLQ stream name"),
):
    """
    Replay messages from the dead letter queue.

    This reads messages from the DLQ and republishes them to their original streams.
    """
    redis_client = get_redis()

    try:
        # Read from DLQ (without consumer group)
        messages = redis_client.xrange(stream, count=limit)

        if not messages:
            rprint("[yellow]No messages in DLQ[/yellow]")
            raise typer.Exit(0)

        rprint(f"[cyan]Found {len(messages)} messages in DLQ[/cyan]")

        from messaging_whatsapp.contracts.envelope import WhatsAppEnvelope

        replayed = 0

        for msg_id, data in messages:
            try:
                envelope = WhatsAppEnvelope.from_stream_message(msg_id, data)
                original_event = envelope.payload.get("original_event", {})

                if not original_event:
                    rprint(f"[yellow]Skipping {msg_id}: no original_event[/yellow]")
                    continue

                original_type = original_event.get("event_type", "")

                # Determine target stream
                if "inbound" in original_type:
                    target_stream = "bc:whatsapp:inbound"
                elif "outbound" in original_type or "queued" in original_type:
                    target_stream = "bc:whatsapp:outbound"
                else:
                    rprint(f"[yellow]Skipping {msg_id}: unknown event type {original_type}[/yellow]")
                    continue

                # Republish
                original_envelope = WhatsAppEnvelope.from_dict(original_event)
                redis_client.xadd(target_stream, original_envelope.to_stream_data())

                # Remove from DLQ
                redis_client.xdel(stream, msg_id)

                replayed += 1
                rprint(f"[green]Replayed {msg_id} to {target_stream}[/green]")

            except Exception as e:
                rprint(f"[red]Failed to replay {msg_id}: {e}[/red]")

        rprint(f"\n[green]Replayed {replayed} messages[/green]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stream_info(
    stream: str = typer.Option("bc:whatsapp:inbound", help="Stream name"),
):
    """
    Show information about a Redis stream.
    """
    redis_client = get_redis()

    try:
        from messaging_whatsapp.streams.groups import get_stream_info

        info = get_stream_info(redis_client, stream)

        rprint(f"\n[cyan]Stream: {stream}[/cyan]")
        rprint(f"  Length: {info.get('length', 0)}")

        if info.get("first_entry"):
            rprint(f"  First entry: {info['first_entry'][0]}")
        if info.get("last_entry"):
            rprint(f"  Last entry: {info['last_entry'][0]}")

        groups = info.get("groups", [])
        if groups:
            rprint(f"\n  Consumer Groups:")
            for group in groups:
                rprint(f"    - {group.get('name')}: {group.get('pending')} pending, {group.get('consumers')} consumers")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def evolution_create_instance(
    tenant_id: str = typer.Argument(..., help="Tenant UUID"),
    instance_name: str = typer.Argument(..., help="Evolution instance name"),
    api_url: str = typer.Option(..., help="Evolution API base URL"),
    api_key: str = typer.Option(..., help="Evolution API key"),
    display_number: str = typer.Option("", help="Display phone number (optional)"),
):
    """
    Create an Evolution API instance and register it for a tenant.

    This creates the instance in Evolution API and registers the binding in our database.
    """
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        rprint(f"[red]Invalid tenant ID: {tenant_id}[/red]")
        raise typer.Exit(1)

    db = get_db()

    try:
        from messaging_whatsapp.providers.evolution import EvolutionInstanceManager

        # Check if binding already exists
        from messaging_whatsapp.persistence.repo import WhatsAppRepository
        repo = WhatsAppRepository(db)
        existing = repo.get_binding_by_instance_name(instance_name)
        if existing:
            rprint(f"[yellow]Binding already exists for instance_name: {instance_name}[/yellow]")
            raise typer.Exit(1)

        # Create instance in Evolution API
        manager = EvolutionInstanceManager(api_url, api_key)
        try:
            instance_response = asyncio.run(manager.create_instance(instance_name))
            rprint(f"[green]Created Evolution instance: {instance_name}[/green]")
        except Exception as e:
            rprint(f"[red]Failed to create Evolution instance: {e}[/red]")
            raise typer.Exit(1)
        finally:
            asyncio.run(manager.close())

        # Encrypt API key
        encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
        encrypted_api_key = None
        if encryption_key:
            from cryptography.fernet import Fernet
            f = Fernet(encryption_key.encode())
            encrypted_api_key = f.encrypt(api_key.encode()).decode()
        else:
            encrypted_api_key = api_key
            rprint("[yellow]Warning: WHATSAPP_ENCRYPTION_KEY not set, storing API key unencrypted[/yellow]")

        # Create binding
        from messaging_whatsapp.persistence.models import WhatsAppTenantBinding
        binding = WhatsAppTenantBinding(
            tenant_id=tenant_uuid,
            provider="evolution",
            instance_name=instance_name,
            api_url=api_url,
            api_key=encrypted_api_key,
            display_number=display_number or instance_name,
        )
        db.add(binding)
        db.commit()

        rprint(f"[green]Successfully registered Evolution instance:[/green]")
        rprint(f"  Instance: {instance_name}")
        rprint(f"  Tenant: {tenant_uuid}")
        rprint(f"  API URL: {api_url}")
        rprint(f"\n[yellow]Next step: Run 'evolution-connect' to connect WhatsApp[/yellow]")

    finally:
        db.close()


@app.command()
def evolution_connect(
    instance_name: str = typer.Argument(..., help="Evolution instance name"),
    show_qr: bool = typer.Option(True, help="Show QR code in terminal"),
):
    """
    Connect an Evolution instance to WhatsApp (generate QR code).

    Scan the QR code with WhatsApp to connect the instance.
    """
    db = get_db()

    try:
        from messaging_whatsapp.persistence.repo import WhatsAppRepository
        repo = WhatsAppRepository(db)
        binding = repo.get_binding_by_instance_name(instance_name)

        if not binding:
            rprint(f"[red]No binding found for instance: {instance_name}[/red]")
            raise typer.Exit(1)

        if binding.provider != "evolution":
            rprint(f"[red]Binding is not an Evolution instance[/red]")
            raise typer.Exit(1)

        # Get API key
        api_key = binding.api_key or ""
        encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
        if encryption_key and api_key:
            try:
                from cryptography.fernet import Fernet
                f = Fernet(encryption_key.encode())
                api_key = f.decrypt(api_key.encode()).decode()
            except Exception as e:
                rprint(f"[yellow]Failed to decrypt API key: {e}[/yellow]")

        # Get QR code
        from messaging_whatsapp.providers.evolution import EvolutionInstanceManager
        manager = EvolutionInstanceManager(binding.api_url or "", api_key)

        try:
            qrcode = asyncio.run(manager.get_qr_code(instance_name))

            if qrcode:
                rprint(f"[green]QR Code for instance: {instance_name}[/green]")
                if show_qr:
                    # Try to display QR code using qrcode library if available
                    try:
                        import qrcode
                        from io import StringIO
                        import base64

                        qr_data = base64.b64decode(qrcode)
                        qr = qrcode.QRCode()
                        qr.add_data(qr_data)
                        qr.print_ascii(invert=True)
                    except ImportError:
                        rprint("[yellow]Install 'qrcode' package to display QR code in terminal[/yellow]")
                        rprint(f"[cyan]QR Code Base64:[/cyan]")
                        rprint(qrcode[:100] + "...")
                else:
                    rprint(f"[cyan]QR Code generated (use --show-qr to display)[/cyan]")
            else:
                # Check instance status
                status = asyncio.run(manager.get_instance_status(instance_name))
                state = status.get("state", "unknown")
                if state == "open":
                    rprint(f"[green]Instance {instance_name} is already connected![/green]")
                else:
                    rprint(f"[yellow]Could not get QR code. Instance state: {state}[/yellow]")

        finally:
            asyncio.run(manager.close())

    finally:
        db.close()


@app.command()
def evolution_list_instances(
    api_url: Optional[str] = typer.Option(None, help="Evolution API URL (or use binding)"),
    api_key: Optional[str] = typer.Option(None, help="Evolution API key (or use binding)"),
    instance_name: Optional[str] = typer.Option(None, help="Filter by instance name"),
):
    """
    List Evolution API instances.

    If api_url and api_key are not provided, will use from bindings in database.
    """
    db = get_db()

    try:
        from messaging_whatsapp.providers.evolution import EvolutionInstanceManager

        # Get API credentials
        if not api_url or not api_key:
            # Try to get from a binding
            from messaging_whatsapp.persistence.repo import WhatsAppRepository
            repo = WhatsAppRepository(db)
            if instance_name:
                binding = repo.get_binding_by_instance_name(instance_name)
            else:
                # Get first Evolution binding
                from sqlalchemy import text
                result = db.execute(
                    text("SELECT api_url, api_key FROM whatsapp_tenant_bindings WHERE provider = 'evolution' AND is_active = true LIMIT 1")
                )
                row = result.fetchone()
                if row:
                    api_url = row[0]
                    api_key = row[1]

            if not api_url or not api_key:
                rprint("[red]Please provide api_url and api_key, or ensure Evolution bindings exist[/red]")
                raise typer.Exit(1)

            # Decrypt API key if needed
            encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
            if encryption_key and api_key:
                try:
                    from cryptography.fernet import Fernet
                    f = Fernet(encryption_key.encode())
                    api_key = f.decrypt(api_key.encode()).decode()
                except Exception:
                    pass

        manager = EvolutionInstanceManager(api_url, api_key)

        try:
            instances = asyncio.run(manager.list_instances())

            if not instances:
                rprint("[yellow]No instances found[/yellow]")
                raise typer.Exit(0)

            table = Table(title="Evolution API Instances")
            table.add_column("Instance Name")
            table.add_column("State")
            table.add_column("Phone Number")
            table.add_column("Integration")

            for inst in instances:
                table.add_row(
                    inst.get("instanceName", "-"),
                    inst.get("state", "unknown"),
                    inst.get("phoneNumber", "-"),
                    inst.get("integration", "-"),
                )

            console.print(table)

        finally:
            asyncio.run(manager.close())

    finally:
        db.close()


@app.command()
def evolution_instance_status(
    instance_name: str = typer.Argument(..., help="Evolution instance name"),
):
    """
    Get status of an Evolution instance.
    """
    db = get_db()

    try:
        from messaging_whatsapp.persistence.repo import WhatsAppRepository
        repo = WhatsAppRepository(db)
        binding = repo.get_binding_by_instance_name(instance_name)

        if not binding or binding.provider != "evolution":
            rprint(f"[red]No Evolution binding found for: {instance_name}[/red]")
            raise typer.Exit(1)

        # Get API key
        api_key = binding.api_key or ""
        encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
        if encryption_key and api_key:
            try:
                from cryptography.fernet import Fernet
                f = Fernet(encryption_key.encode())
                api_key = f.decrypt(api_key.encode()).decode()
            except Exception:
                pass

        from messaging_whatsapp.providers.evolution import EvolutionInstanceManager
        manager = EvolutionInstanceManager(binding.api_url or "", api_key)

        try:
            status = asyncio.run(manager.get_instance_status(instance_name))

            if not status:
                rprint(f"[yellow]Instance {instance_name} not found in Evolution API[/yellow]")
                raise typer.Exit(1)

            rprint(f"\n[cyan]Instance: {instance_name}[/cyan]")
            rprint(f"  State: {status.get('state', 'unknown')}")
            rprint(f"  Phone Number: {status.get('phoneNumber', '-')}")
            rprint(f"  Integration: {status.get('integration', '-')}")
            rprint(f"  Created: {status.get('createdAt', '-')}")

        finally:
            asyncio.run(manager.close())

    finally:
        db.close()


if __name__ == "__main__":
    app()

