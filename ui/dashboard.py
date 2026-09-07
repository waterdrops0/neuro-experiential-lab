from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy


class MetricValue(QLabel):
    """Keep a readable, content-derived minimum even before data arrives."""
    def minimumSizeHint(self):
        self.ensurePolished()
        metrics = self.fontMetrics()
        # Reserve the longest normal status/state so updates do not resize columns.
        width = max(metrics.horizontalAdvance(text) for text in
                    ('DISCONNECTED', 'PERSPECTIVE', self.text()))
        return super().minimumSizeHint().expandedTo(QSize(width + 4, metrics.height()))

    def sizeHint(self):
        return super().sizeHint().expandedTo(self.minimumSizeHint())

class MetricCard(QFrame):
    def __init__(self, title, unit=''):
        super().__init__()
        self.setObjectName('metric')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        self.value = MetricValue('—')
        self.value.setObjectName('metricValue')
        self.value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.value.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
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
