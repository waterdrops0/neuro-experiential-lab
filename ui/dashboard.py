from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class MetricCard(QFrame):
    def __init__(self, title, unit=''):
        super().__init__()
        self.setObjectName('metric')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        self.value = QLabel('—')
        self.value.setObjectName('metricValue')
        layout.addWidget(self.value)
        if unit:
            layout.addWidget(QLabel(unit))

    def set_value(self, value):
        self.value.setText(str(value))

STYLE = '''
QMainWindow, QWidget { background: #0b1420; color: #dfe9f2; font-size: 13px; }
QFrame#metric { background: #132234; border: 1px solid #263b50; border-radius: 8px; }
QFrame#metric QLabel { background: transparent; }
QLabel#metricValue { font-size: 30px; font-weight: 600; color: #55ddbc; }
QLabel#title { font-size: 22px; font-weight: 600; }
QPushButton { background: #203349; border: 1px solid #3b536c; border-radius: 5px; padding: 10px; font-weight: 600; }
QPushButton:hover { background: #304b65; }
QPushButton:checked { background: #186959; border: 2px solid #55ddbc; }
QPushButton:disabled { color: #637386; background: #172332; }
QPushButton#stop { background: #a53140; color: white; font-size: 17px; }
QLineEdit, QSpinBox, QListWidget { background: #132234; border: 1px solid #30455b; padding: 7px; }
QProgressBar { background: #132234; border: 1px solid #30455b; min-height: 20px; text-align: center; }
QProgressBar::chunk { background: #42b99b; }
'''
