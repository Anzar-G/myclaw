"""Non-destructive startup and configuration diagnostic."""

from config.settings import settings
from config.tool_registry import ToolRegistry


def main() -> int:
    registry = ToolRegistry()
    print(f"Tool registry: OK ({len(registry.tools)} tools)")
    for name, configured in settings.validate_required_services().items():
        print(f"{name}: {'configured' if configured else 'not configured'}")
    print("No macOS action was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
