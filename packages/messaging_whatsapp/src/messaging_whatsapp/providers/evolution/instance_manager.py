"""
Evolution API Instance Manager

Manages Evolution API instances (create, connect, disconnect, status).
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EvolutionInstanceManager:
    """
    Manages Evolution API instances.

    Each tenant can have one Evolution instance identified by instance_name.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        timeout: float = 30.0,
    ):
        """
        Initialize instance manager.

        Args:
            api_url: Base URL of Evolution API
            api_key: API key for authentication
            timeout: HTTP request timeout
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "apikey": self.api_key,
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        client = await self._get_client()
        url = f"{self.api_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=json_data)

            response_data = response.json()

            if response.status_code >= 400:
                error = response_data.get("error") or response_data.get("message", "Unknown error")
                raise Exception(f"API error: {error}")

            return response_data

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    async def create_instance(
        self,
        instance_name: str,
        qrcode: bool = True,
        integration: str = "WHATSAPP-BAILEYS",
    ) -> dict[str, Any]:
        """
        Create a new Evolution API instance.

        Args:
            instance_name: Unique name for the instance
            qrcode: Whether to return QR code for connection
            integration: Integration type (WHATSAPP-BAILEYS, etc)

        Returns:
            Instance creation response with QR code if requested
        """
        endpoint = "/instance/create"

        payload = {
            "instanceName": instance_name,
            "qrcode": qrcode,
            "integration": integration,
        }

        return await self._make_request("POST", endpoint, payload)

    async def connect_instance(
        self,
        instance_name: str,
    ) -> dict[str, Any]:
        """
        Connect/initialize an instance (generate QR code).

        Args:
            instance_name: Name of the instance

        Returns:
            Connection response with QR code
        """
        endpoint = f"/instance/connect/{instance_name}"

        return await self._make_request("GET", endpoint)

    async def get_qr_code(
        self,
        instance_name: str,
    ) -> str | None:
        """
        Get QR code for instance connection.

        Args:
            instance_name: Name of the instance

        Returns:
            QR code base64 string or None
        """
        try:
            response = await self.connect_instance(instance_name)
            qrcode = response.get("qrcode", {}).get("base64")
            return qrcode
        except Exception as e:
            logger.error(f"Failed to get QR code: {e}")
            return None

    async def get_instance_status(
        self,
        instance_name: str,
    ) -> dict[str, Any]:
        """
        Get status of an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            Status information (state, phone number, etc)
        """
        endpoint = f"/instance/fetchInstances"

        try:
            response = await self._make_request("GET", endpoint)
            instances = response.get("instance", [])

            for instance in instances:
                if instance.get("instanceName") == instance_name:
                    return instance

            return {}

        except Exception as e:
            logger.error(f"Failed to get instance status: {e}")
            return {}

    async def list_instances(self) -> list[dict[str, Any]]:
        """
        List all instances.

        Returns:
            List of instance information
        """
        endpoint = "/instance/fetchInstances"

        try:
            response = await self._make_request("GET", endpoint)
            return response.get("instance", [])

        except Exception as e:
            logger.error(f"Failed to list instances: {e}")
            return []

    async def delete_instance(
        self,
        instance_name: str,
    ) -> bool:
        """
        Delete an instance.

        Args:
            instance_name: Name of the instance to delete

        Returns:
            True if successful
        """
        endpoint = f"/instance/delete/{instance_name}"

        try:
            await self._make_request("DELETE", endpoint)
            return True
        except Exception as e:
            logger.error(f"Failed to delete instance: {e}")
            return False

    async def logout_instance(
        self,
        instance_name: str,
    ) -> bool:
        """
        Logout/disconnect an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            True if successful
        """
        endpoint = f"/instance/logout/{instance_name}"

        try:
            await self._make_request("DELETE", endpoint)
            return True
        except Exception as e:
            logger.error(f"Failed to logout instance: {e}")
            return False

    async def restart_instance(
        self,
        instance_name: str,
    ) -> bool:
        """
        Restart an instance.

        Args:
            instance_name: Name of the instance

        Returns:
            True if successful
        """
        endpoint = f"/instance/restart/{instance_name}"

        try:
            await self._make_request("PUT", endpoint)
            return True
        except Exception as e:
            logger.error(f"Failed to restart instance: {e}")
            return False




