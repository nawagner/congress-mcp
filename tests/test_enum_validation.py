"""Tests for enum validation middleware."""

from __future__ import annotations

import pytest

from congress_mcp.middleware import (
    EnumValidationMiddleware,
    _format_prescriptive_error,
    _resolve_enum_class,
)
from congress_mcp.types.enums import (
    AmendmentType,
    AmendmentTypeLiteral,
    BillType,
    BillTypeLiteral,
    Chamber,
    ChamberLiteral,
    HouseCommunicationType,
    HouseCommunicationTypeLiteral,
    LawType,
    LawTypeLiteral,
    ReportType,
    ReportTypeLiteral,
    SenateCommunicationType,
    SenateCommunicationTypeLiteral,
)


# ---------------------------------------------------------------------------
# _resolve_enum_class
# ---------------------------------------------------------------------------


class TestResolveEnumClass:
    def test_bill_type(self) -> None:
        assert _resolve_enum_class("bill_type", "get_bill") is BillType

    def test_chamber(self) -> None:
        assert _resolve_enum_class("chamber", "list_committees_by_chamber") is Chamber

    def test_amendment_type(self) -> None:
        assert _resolve_enum_class("amendment_type", "get_amendment") is AmendmentType

    def test_law_type(self) -> None:
        assert _resolve_enum_class("law_type", "get_law") is LawType

    def test_report_type(self) -> None:
        assert _resolve_enum_class("report_type", "get_committee_report") is ReportType

    def test_communication_type_house(self) -> None:
        assert (
            _resolve_enum_class("communication_type", "list_house_communications")
            is HouseCommunicationType
        )

    def test_communication_type_senate(self) -> None:
        assert (
            _resolve_enum_class("communication_type", "list_senate_communications")
            is SenateCommunicationType
        )

    def test_communication_type_get_house(self) -> None:
        assert (
            _resolve_enum_class("communication_type", "get_house_communication")
            is HouseCommunicationType
        )

    def test_communication_type_get_senate(self) -> None:
        assert (
            _resolve_enum_class("communication_type", "get_senate_communication")
            is SenateCommunicationType
        )

    def test_unknown_field(self) -> None:
        assert _resolve_enum_class("unknown_field", "some_tool") is None


# ---------------------------------------------------------------------------
# _format_prescriptive_error
# ---------------------------------------------------------------------------


class TestFormatPrescriptiveError:
    """Test prescriptive error message generation."""

    # -- None/null inputs --------------------------------------------------

    def test_none_bill_type(self) -> None:
        msg = _format_prescriptive_error("bill_type", None, "get_bill")
        assert msg is not None
        assert "null/None is not valid" in msg
        assert "REQUIRED" in msg
        assert "hr" in msg
        assert "sres" in msg
        assert "Please retry" in msg

    def test_none_chamber(self) -> None:
        msg = _format_prescriptive_error("chamber", None, "list_hearings")
        assert msg is not None
        assert "null/None is not valid" in msg
        assert "house" in msg
        assert "senate" in msg

    def test_none_amendment_type(self) -> None:
        msg = _format_prescriptive_error("amendment_type", None, "get_amendment")
        assert msg is not None
        assert "hamdt" in msg
        assert "samdt" in msg
        assert "suamdt" in msg

    def test_none_law_type(self) -> None:
        msg = _format_prescriptive_error("law_type", None, "get_law")
        assert msg is not None
        assert "pub" in msg
        assert "priv" in msg

    def test_none_report_type(self) -> None:
        msg = _format_prescriptive_error("report_type", None, "get_committee_report")
        assert msg is not None
        assert "hrpt" in msg
        assert "srpt" in msg
        assert "erpt" in msg

    def test_none_house_communication_type(self) -> None:
        msg = _format_prescriptive_error(
            "communication_type", None, "list_house_communications"
        )
        assert msg is not None
        assert "ec" in msg
        assert "ml" in msg
        # Confirm it is NOT showing Senate-only values
        assert "pom" not in msg

    def test_none_senate_communication_type(self) -> None:
        msg = _format_prescriptive_error(
            "communication_type", None, "list_senate_communications"
        )
        assert msg is not None
        assert "ec" in msg
        assert "pom" in msg
        # Confirm it is NOT showing House-only values
        assert "ml" not in msg

    # -- Invalid string inputs ---------------------------------------------

    def test_invalid_bill_type(self) -> None:
        msg = _format_prescriptive_error("bill_type", "invalid", "get_bill")
        assert msg is not None
        assert "'invalid' is not valid" in msg
        assert "hr" in msg
        assert "REQUIRED" not in msg  # Only shown for None

    def test_invalid_chamber(self) -> None:
        msg = _format_prescriptive_error("chamber", "both", "list_hearings")
        assert msg is not None
        assert "'both' is not valid" in msg
        assert "house" in msg
        assert "senate" in msg

    # -- Boolean inputs (the exact bug reported) -----------------------------

    def test_boolean_true_amendment_type(self) -> None:
        msg = _format_prescriptive_error("amendment_type", True, "get_amendment")
        assert msg is not None
        assert "Boolean True" in msg
        assert "STRING" in msg
        assert "not a boolean" in msg
        assert "hamdt" in msg
        assert "samdt" in msg
        assert "suamdt" in msg

    def test_boolean_false_bill_type(self) -> None:
        msg = _format_prescriptive_error("bill_type", False, "get_bill")
        assert msg is not None
        assert "Boolean False" in msg
        assert "STRING" in msg
        assert "hr" in msg

    def test_boolean_true_chamber(self) -> None:
        msg = _format_prescriptive_error("chamber", True, "list_hearings")
        assert msg is not None
        assert "Boolean True" in msg
        assert "house" in msg
        assert "senate" in msg

    # -- Unknown fields return None ----------------------------------------

    def test_unknown_field_returns_none(self) -> None:
        assert _format_prescriptive_error("congress", 118, "get_bill") is None

    def test_unknown_field_with_none_value(self) -> None:
        assert _format_prescriptive_error("unknown", None, "some_tool") is None


# ---------------------------------------------------------------------------
# EnumValidationMiddleware integration
# ---------------------------------------------------------------------------


class TestEnumValidationMiddleware:
    """Test the middleware catches ValidationError and raises ToolError."""

    @pytest.fixture()
    def middleware(self) -> EnumValidationMiddleware:
        return EnumValidationMiddleware()

    @pytest.mark.asyncio()
    async def test_valid_call_passes_through(self, middleware: EnumValidationMiddleware) -> None:
        """Middleware should not interfere with successful tool calls."""
        from unittest.mock import AsyncMock, MagicMock

        sentinel = object()
        call_next = AsyncMock(return_value=sentinel)

        context = MagicMock()
        context.message.name = "list_bills"

        result = await middleware.on_call_tool(context, call_next)
        assert result is sentinel
        call_next.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test_catches_enum_validation_error(
        self, middleware: EnumValidationMiddleware
    ) -> None:
        """Middleware should convert enum ValidationError to ToolError."""
        from unittest.mock import AsyncMock, MagicMock

        from fastmcp.exceptions import ToolError
        from pydantic import BaseModel, ValidationError

        # Use a model with a named field to produce realistic loc tuples
        class FakeBillParams(BaseModel):
            bill_type: BillType

        with pytest.raises(ValidationError) as exc_info:
            FakeBillParams.model_validate({"bill_type": None})
        pydantic_error = exc_info.value

        call_next = AsyncMock(side_effect=pydantic_error)
        context = MagicMock()
        context.message.name = "list_bills_by_type"

        with pytest.raises(ToolError) as tool_exc_info:
            await middleware.on_call_tool(context, call_next)

        error_msg = str(tool_exc_info.value)
        assert "null/None is not valid" in error_msg
        assert "bill_type" in error_msg
        assert "hr" in error_msg
        assert "Please retry" in error_msg

    @pytest.mark.asyncio()
    async def test_catches_invalid_string_validation_error(
        self, middleware: EnumValidationMiddleware
    ) -> None:
        """Middleware should handle invalid string enum values."""
        from unittest.mock import AsyncMock, MagicMock

        from fastmcp.exceptions import ToolError
        from pydantic import BaseModel, ValidationError

        class FakeChamberParams(BaseModel):
            chamber: Chamber

        with pytest.raises(ValidationError) as exc_info:
            FakeChamberParams.model_validate({"chamber": "both"})
        pydantic_error = exc_info.value

        call_next = AsyncMock(side_effect=pydantic_error)
        context = MagicMock()
        context.message.name = "list_committees_by_chamber"

        with pytest.raises(ToolError) as tool_exc_info:
            await middleware.on_call_tool(context, call_next)

        error_msg = str(tool_exc_info.value)
        assert "chamber" in error_msg
        assert "house" in error_msg
        assert "senate" in error_msg

    @pytest.mark.asyncio()
    async def test_non_enum_validation_error_still_raises_tool_error(
        self, middleware: EnumValidationMiddleware
    ) -> None:
        """Non-enum ValidationErrors should still be caught and wrapped."""
        from unittest.mock import AsyncMock, MagicMock

        from fastmcp.exceptions import ToolError
        from pydantic import TypeAdapter, ValidationError

        # Create a non-enum validation error (int field getting a string)
        adapter = TypeAdapter(int)
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python("not_a_number")
        pydantic_error = exc_info.value

        call_next = AsyncMock(side_effect=pydantic_error)
        context = MagicMock()
        context.message.name = "list_bills"

        with pytest.raises(ToolError):
            await middleware.on_call_tool(context, call_next)

    @pytest.mark.asyncio()
    async def test_non_validation_errors_propagate(
        self, middleware: EnumValidationMiddleware
    ) -> None:
        """Non-ValidationError exceptions should propagate unchanged."""
        from unittest.mock import AsyncMock, MagicMock

        call_next = AsyncMock(side_effect=RuntimeError("something else"))
        context = MagicMock()
        context.message.name = "get_bill"

        with pytest.raises(RuntimeError, match="something else"):
            await middleware.on_call_tool(context, call_next)


# ---------------------------------------------------------------------------
# Literal type schema tests — verifying $ref elimination
# ---------------------------------------------------------------------------


class TestLiteralSchemaFlatness:
    """Verify Literal types produce flat JSON schemas without $ref/$defs."""

    @pytest.mark.parametrize(
        "literal_type",
        [
            AmendmentTypeLiteral,
            BillTypeLiteral,
            ChamberLiteral,
            LawTypeLiteral,
            ReportTypeLiteral,
            HouseCommunicationTypeLiteral,
            SenateCommunicationTypeLiteral,
        ],
    )
    def test_literal_schema_has_no_ref(self, literal_type: type) -> None:
        """Literal types should produce inline enum+type, not $ref/$defs."""
        from typing import Annotated

        from pydantic import Field, TypeAdapter

        from fastmcp.utilities.json_schema import compress_schema

        # Simulate how FastMCP builds the tool schema
        ta = TypeAdapter(Annotated[literal_type, Field(description="test")])
        schema = ta.json_schema()
        schema = compress_schema(schema, prune_titles=True)

        assert "$ref" not in str(schema), f"Schema contains $ref: {schema}"
        assert "$defs" not in schema, f"Schema contains $defs: {schema}"
        assert "enum" in schema, f"Schema missing enum constraint: {schema}"
        assert "type" in schema, f"Schema missing type constraint: {schema}"
        assert schema["type"] == "string"
