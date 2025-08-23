from .document import Document

class App:
    def __init__(self):
        self.window = None
        self.document = Document(64, 64)

    def set_window(self, window):
        self.window = window

    def exit(self):
        if self.window:
            self.window.close()
