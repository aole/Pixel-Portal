from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QFileDialog, QColorDialog, QListWidget, QListWidgetItem, QCheckBox, QWidget, QHBoxLayout
from PySide6.QtGui import QImage, QColor, QPixmap
import numpy as np
from sklearn.cluster import KMeans
from PIL import Image
import os

class PaletteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Palette from Image")
        self.setMinimumSize(400, 300)

        self.layout = QVBoxLayout(self)

        self.open_image_button = QPushButton("Open Image")
        self.open_image_button.clicked.connect(self.open_image)
        self.layout.addWidget(self.open_image_button)

        self.color_list_widget = QListWidget()
        self.layout.addWidget(self.color_list_widget)

        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        self.colors = []

    def open_image(self):
        self.last_directory = os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            self.last_directory,
            "Image Files (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.extract_colors(file_path)

    def extract_colors(self, image_path):
        try:
            image = Image.open(image_path).convert("RGB")
            image_np = np.array(image)
            pixels = image_np.reshape(-1, 3)

            kmeans = KMeans(n_clusters=16, random_state=42, n_init=10)
            kmeans.fit(pixels)
            self.colors = kmeans.cluster_centers_.astype(int)

            self.update_color_list()
        except Exception as e:
            print(f"Error extracting colors: {e}")

    def update_color_list(self):
        self.color_list_widget.clear()
        for color in self.colors:
            q_color = QColor(color[0], color[1], color[2])
            item_widget = self.create_color_item_widget(q_color)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.color_list_widget.addItem(list_item)
            self.color_list_widget.setItemWidget(list_item, item_widget)

    def create_color_item_widget(self, color):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        layout.addWidget(checkbox)

        color_button = QPushButton()
        color_button.setFixedSize(24, 24)
        pixmap = QPixmap(24, 24)
        pixmap.fill(color)
        color_button.setIcon(pixmap)
        color_button.clicked.connect(lambda: self.change_color(color_button, checkbox))
        layout.addWidget(color_button)

        return widget

    def change_color(self, color_button, checkbox):
        # Extract color from the icon's pixmap
        pixmap = color_button.icon().pixmap(24, 24)
        image = pixmap.toImage()
        current_color = image.pixelColor(0, 0)

        new_color = QColorDialog.getColor(current_color, self)
        if new_color.isValid():
            pixmap = QPixmap(24, 24)
            pixmap.fill(new_color)
            color_button.setIcon(pixmap)
            checkbox.setChecked(True)

    def get_selected_colors(self):
        selected_colors = []
        for i in range(self.color_list_widget.count()):
            item = self.color_list_widget.item(i)
            widget = self.color_list_widget.itemWidget(item)
            checkbox = widget.findChild(QCheckBox)
            if checkbox.isChecked():
                color_button = widget.findChild(QPushButton)
                color = color_button.icon().pixmap(24, 24).toImage().pixelColor(0, 0)
                selected_colors.append(color.name())
        return selected_colors
