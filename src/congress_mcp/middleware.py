"""Middleware for improving validation error messages for LLM clients."""

from __future__ import annotations

from enum import Enum
from typing import Any

import mcp.types as mt
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult
from pydantic import ValidationError

from congress_mcp.types.enums import (
    AmendmentType,
    BillType,
    Chamber,
    HouseCommunicationType,
    LawType,
    ReportType,
    SenateCommunicationType,
)

# Map parameter names to their enum class for prescriptive error messages.
# communication_type is intentionally omitted — it requires disambiguation
# between House and Senate based on the tool name (see _resolve_enum_class).
ENUM_PARAMS: dict[str, type[Enum]] = {
    "bill_type": BillType,
    "chamber": Chamber,
    "amendment_type": AmendmentType,
    "law_type": LawType,
    "report_type": ReportType,
}


def _resolve_enum_class(field_name: str, tool_name: str) -> type[Enum] | None:
    """Resolve the enum class for a given parameter name and tool.

    Handles the special case where ``communication_type`` maps to different
    enum types depending on whether the tool is House or Senate.
    """
    if field_name == "communication_type":
        if "house" in tool_name:
            return HouseCommunicationType
        return SenateCommunicationType
    return ENUM_PARAMS.get(field_name)


def _valid_values_str(enum_cls: type[Enum]) -> str:
    return ", ".join(member.value for member in enum_cls)


def _format_prescriptive_error(
    field_name: str,
    input_value: Any,
    tool_name: str,
) -> str | None:
    """Build a prescriptive error message for an invalid enum value.

    Returns ``None`` if *field_name* is not a recognised enum parameter.
    """
    enum_cls = _resolve_enum_class(field_name, tool_name)
    if enum_cls is None:
        return None

    valid = _valid_values_str(enum_cls)

    if input_value is None:
        return (
            f"null/None is not valid for '{field_name}'. "
            f"This field is REQUIRED and cannot be null. "
            f"Must be one of: {valid}. "
            f"Please retry with one of these exact string values."
        )

    if isinstance(input_value, bool):
        example = next(iter(enum_cls)).value
        return (
            f"Boolean {input_value} is not valid for '{field_name}'. "
            f"This field requires a STRING value, not a boolean. "
            f"Must be one of: {valid}. "
            f'Please retry with one of these exact string values (e.g. "{example}").'
        )

    return (
        f"'{input_value}' is not valid for '{field_name}'. "
        f"Must be one of: {valid}. "
        f"Please retry with one of these exact string values."
    )


class EnumValidationMiddleware(Middleware):
    """Intercept Pydantic ``ValidationError`` for enum parameters and re-raise
    as ``ToolError`` with prescriptive messages that help LLM clients
    self-correct instead of retrying with the same invalid value."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        try:
            return await call_next(context)
        except ValidationError as exc:
            tool_name = context.message.name
            prescriptive_parts: list[str] = []

            for error in exc.errors():
                loc = error.get("loc", ())
                field_name = str(loc[-1]) if loc else "unknown"
                input_value = error.get("input")

                msg = _format_prescriptive_error(field_name, input_value, tool_name)
                if msg:
                    prescriptive_parts.append(msg)

            if prescriptive_parts:
                raise ToolError("\n".join(prescriptive_parts)) from exc

            # Non-enum validation error — re-raise with the original message
            raise ToolError(str(exc)) from exc
