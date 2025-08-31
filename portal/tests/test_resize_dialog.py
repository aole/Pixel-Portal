from portal.resize_dialog import ResizeDialog

def test_get_values(qtbot):
    """Test that the correct width, height, and interpolation values are returned from the dialog."""
    dialog = ResizeDialog(width=100, height=100)
    qtbot.addWidget(dialog)

    dialog.width_input.setText("200")
    dialog.height_input.setText("200")
    dialog.interpolation_combo.setCurrentText("Smooth")

    values = dialog.get_values()

    assert values["width"] == 200
    assert values["height"] == 200
    assert values["interpolation"] == "Smooth"
