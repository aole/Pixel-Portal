class App:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def exit(self):
        if self.window:
            self.window.close()
