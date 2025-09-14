import os
import importlib
from portal.tools.basetool import BaseTool

def get_tools():
    """
    Dynamically discover and import all tool classes in this directory.
    """
    tools = []
    tools_dir = os.path.dirname(__file__)

    for filename in os.listdir(tools_dir):
        if filename.endswith("tool.py") and filename != "basetool.py":
            module_name = f"portal.tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (
                    isinstance(attribute, type)
                    and issubclass(attribute, BaseTool)
                    and attribute is not BaseTool
                    and getattr(attribute, "name", None)
                ):
                    tools.append(
                        {
                            "class": attribute,
                            "name": attribute.name,
                            "icon": getattr(attribute, "icon", None),
                            "shortcut": getattr(attribute, "shortcut", None),
                            "category": getattr(attribute, "category", None),
                        }
                    )
    return tools
