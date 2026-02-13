"""
WhatsApp Template Registry

Manages approved message templates for WhatsApp Business.
Templates must be pre-approved in the Meta Business Manager.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateParameter:
    """A parameter in a template component."""

    name: str
    type: str = "text"  # text, currency, date_time, image, document, video
    required: bool = True


@dataclass
class TemplateComponent:
    """A component of a template (header, body, button)."""

    type: str  # header, body, button
    parameters: list[TemplateParameter] = field(default_factory=list)
    button_index: int | None = None  # For button components


@dataclass
class MessageTemplate:
    """
    A WhatsApp message template.

    Templates must be approved in Meta Business Manager before use.
    """

    name: str
    language: str = "pt_BR"
    category: str = "UTILITY"  # UTILITY, MARKETING, AUTHENTICATION
    components: list[TemplateComponent] = field(default_factory=list)
    description: str = ""

    def build_components(self, variables: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Build template components payload from variables.

        Args:
            variables: Dict mapping parameter names to values

        Returns:
            Components list for API request
        """
        result = []

        for component in self.components:
            comp_data: dict[str, Any] = {"type": component.type}
            parameters = []

            for param in component.parameters:
                value = variables.get(param.name)
                if value is None and param.required:
                    raise ValueError(f"Missing required parameter: {param.name}")

                if value is not None:
                    if param.type == "text":
                        parameters.append({"type": "text", "text": str(value)})
                    elif param.type == "currency":
                        parameters.append({
                            "type": "currency",
                            "currency": value,
                        })
                    elif param.type == "image":
                        parameters.append({
                            "type": "image",
                            "image": {"link": value} if isinstance(value, str) else value,
                        })

            if parameters:
                comp_data["parameters"] = parameters

            if component.button_index is not None:
                comp_data["index"] = component.button_index

            result.append(comp_data)

        return result


class TemplateRegistry:
    """
    Registry of approved message templates.

    Templates are registered by name and can be looked up for sending.
    """

    def __init__(self) -> None:
        self._templates: dict[str, MessageTemplate] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default templates for common use cases."""

        # Quote created notification
        self.register(MessageTemplate(
            name="quote_created_template",
            language="pt_BR",
            category="UTILITY",
            description="Notify customer that a quote was created",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="customer_name"),
                        TemplateParameter(name="quote_number"),
                        TemplateParameter(name="total_value"),
                    ],
                ),
            ],
        ))

        # Order status notification
        self.register(MessageTemplate(
            name="order_status_template",
            language="pt_BR",
            category="UTILITY",
            description="Notify customer of order status change",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="customer_name"),
                        TemplateParameter(name="order_number"),
                        TemplateParameter(name="status"),
                    ],
                ),
            ],
        ))

        # Delivery started notification
        self.register(MessageTemplate(
            name="delivery_started_template",
            language="pt_BR",
            category="UTILITY",
            description="Notify customer that delivery has started",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="customer_name"),
                        TemplateParameter(name="order_number"),
                        TemplateParameter(name="estimated_time", required=False),
                    ],
                ),
            ],
        ))

        # Delivery completed notification
        self.register(MessageTemplate(
            name="delivery_completed_template",
            language="pt_BR",
            category="UTILITY",
            description="Notify customer that delivery is complete",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="customer_name"),
                        TemplateParameter(name="order_number"),
                    ],
                ),
            ],
        ))

        # Welcome message
        self.register(MessageTemplate(
            name="welcome_template",
            language="pt_BR",
            category="UTILITY",
            description="Welcome message for new conversations",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="business_name"),
                    ],
                ),
            ],
        ))

        # Auto-reply message
        self.register(MessageTemplate(
            name="auto_reply_template",
            language="pt_BR",
            category="UTILITY",
            description="Automatic reply when message is received",
            components=[
                TemplateComponent(
                    type="body",
                    parameters=[
                        TemplateParameter(name="customer_name", required=False),
                    ],
                ),
            ],
        ))

    def register(self, template: MessageTemplate) -> None:
        """Register a template."""
        self._templates[template.name] = template

    def get(self, name: str) -> MessageTemplate | None:
        """Get a template by name."""
        return self._templates.get(name)

    def get_or_raise(self, name: str) -> MessageTemplate:
        """Get a template by name, raising if not found."""
        template = self.get(name)
        if template is None:
            raise ValueError(f"Template not found: {name}")
        return template

    def list_templates(self) -> list[str]:
        """List all registered template names."""
        return list(self._templates.keys())

    def build_payload(
        self,
        template_name: str,
        variables: dict[str, Any],
        language: str | None = None,
    ) -> dict[str, Any]:
        """
        Build the template payload for API request.

        Args:
            template_name: Name of the template
            variables: Variables to fill in the template
            language: Override template language

        Returns:
            Dict with name, language, and components for API
        """
        template = self.get_or_raise(template_name)

        return {
            "name": template.name,
            "language": {"code": language or template.language},
            "components": template.build_components(variables),
        }


# Global template registry instance
template_registry = TemplateRegistry()




