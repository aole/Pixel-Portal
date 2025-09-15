from __future__ import annotations

import importlib
import os
from importlib.metadata import entry_points
from typing import Dict, List, Type

from .basetool import BaseTool


class ToolRegistry:
    """Registry for built-in and external tools."""

    def __init__(self) -> None:
        self._tools: List[Dict] = []

    # ------------------------------------------------------------------
    def register_tool(self, tool_cls: Type[BaseTool]) -> None:
        """Register a :class:`BaseTool` subclass.

        Parameters
        ----------
        tool_cls:
            The tool class to register.
        """

        if not isinstance(tool_cls, type) or not issubclass(tool_cls, BaseTool):
            raise TypeError("tool_cls must be a subclass of BaseTool")
        if tool_cls is BaseTool:
            return
        if not getattr(tool_cls, "name", None):
            return
        # Avoid duplicates
        if any(t["class"] is tool_cls for t in self._tools):
            return
        self._tools.append(
            {
                "class": tool_cls,
                "name": tool_cls.name,
                "icon": getattr(tool_cls, "icon", None),
                "shortcut": getattr(tool_cls, "shortcut", None),
                "category": getattr(tool_cls, "category", None),
            }
        )

    # ------------------------------------------------------------------
    def get_tools(self) -> List[Dict]:
        """Return registered tools."""

        return list(self._tools)

    # ------------------------------------------------------------------
    def load_builtin_tools(self) -> None:
        """Discover and register built-in tools located in this package."""

        tools_dir = os.path.dirname(__file__)
        for filename in os.listdir(tools_dir):
            if not filename.endswith("tool.py"):
                continue
            if filename in {"basetool.py", "registry.py"}:
                continue
            module_name = f"{__package__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseTool)
                    and attr is not BaseTool
                    and getattr(attr, "name", None)
                ):
                    self.register_tool(attr)

    # ------------------------------------------------------------------
    def load_external_tools(self) -> None:
        """Load tools provided by external packages via entry points."""

        try:
            eps = entry_points(group="pixel_portal.tools")
        except TypeError:  # Python < 3.10 compatibility
            eps = entry_points().get("pixel_portal.tools", [])
        for ep in eps:
            try:
                tool_cls = ep.load()
                self.register_tool(tool_cls)
            except Exception:
                # Ignore badly defined entry points
                continue


__all__ = ["ToolRegistry"]
