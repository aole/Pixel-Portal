from portal.tools import get_tools

def test_get_tools():
    """
    This test should verify that all tool classes are dynamically discovered and imported.
    """
    tools = get_tools()
    assert len(tools) > 0

    expected_tool_names = [
        "BucketTool",
        "EllipseTool",
        "EraserTool",
        "LineTool",
        "MoveTool",
        "PenTool",
        "PickerTool",
        "RectangleTool",
        "SelectCircleTool",
        "SelectColorTool",
        "SelectLassoTool",
        "SelectRectangleTool",
    ]

    actual_tool_names = [tool.__name__ for tool in tools]

    for tool_name in expected_tool_names:
        assert tool_name in actual_tool_names
