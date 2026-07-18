from .mock_banking import get_account_turnover, get_cic_snapshot, get_customer_snapshot, get_kyc_aml_snapshot
from .registry import ToolDefinition, ToolRegistry


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="get_customer_snapshot", handler=get_customer_snapshot, read_only=True))
    registry.register(ToolDefinition(name="get_account_turnover", handler=get_account_turnover, read_only=True))
    registry.register(ToolDefinition(name="get_cic_snapshot", handler=get_cic_snapshot, read_only=True))
    registry.register(ToolDefinition(name="get_kyc_aml_snapshot", handler=get_kyc_aml_snapshot, read_only=True))
    return registry
