"""Tool registration and discovery utilities."""

from .registry import ToolRegistry

# Global registry instance used throughout the application
registry = ToolRegistry()
registry.load_builtin_tools()
registry.load_external_tools()

# Backwards compatible helper functions

def register_tool(tool_cls):
    registry.register_tool(tool_cls)


def get_tools():
    return registry.get_tools()

__all__ = ["ToolRegistry", "registry", "register_tool", "get_tools"]
