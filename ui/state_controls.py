from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtGui import QShortcut, QKeySequence
from core.models import STATES

class StateControls(QWidget):
    def __init__(self, callback, shortcut_parent):
        super().__init__()
        layout = QHBoxLayout(self)
        self.buttons = {}
        self.shortcuts = []
        for index, name in enumerate(STATES, 1):
            button = QPushButton(f'{index}  {name}')
            button.setMinimumHeight(62)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, n=name: callback(n))
            layout.addWidget(button)
            self.buttons[name] = button
            shortcut = QShortcut(QKeySequence(str(index)), shortcut_parent)
            shortcut.activated.connect(lambda n=name: callback(n))
            self.shortcuts.append(shortcut)
        self.set_active('SAFE')

    def set_active(self, name):
        for key, button in self.buttons.items():
            button.setChecked(key == name)
