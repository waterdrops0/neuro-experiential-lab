from PySide6.QtCore import QRect, QSize
from PySide6.QtWidgets import QLayout


class ButtonFlowLayout(QLayout):
    """Keep the existing button row, wrapping only when it cannot fit."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), False)

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(),
                            margins.top() + margins.bottom())

    def sizeHint(self):
        margins = self.contentsMargins()
        return QSize(sum(item.sizeHint().width() for item in self.items)
                     + max(0, len(self.items) - 1) * self.spacing()
                     + margins.left() + margins.right(),
                     self.minimumSize().height())

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, True)

    def _arrange(self, rect, apply):
        margins = self.contentsMargins()
        area = rect.marginsRemoved(margins)
        spacing = self.spacing()
        rows, row, used = [], [], 0
        for item in self.items:
            size = item.sizeHint().expandedTo(item.minimumSize())
            # PAUSE and RESUME share the explicitly reserved minimum width.
            width = size.width()
            if row and used + spacing + width > area.width():
                rows.append(row)
                row, used = [], 0
            used += (spacing if row else 0) + width
            row.append((item, size))
        if row:
            rows.append(row)
        y = area.y()
        for row in rows:
            height = max(size.height() for _, size in row)
            remaining = max(0, area.width() - sum(size.width() for _, size in row)
                            - spacing * (len(row) - 1))
            x = area.x()
            for index, (item, size) in enumerate(row):
                width = size.width() + remaining // len(row) + (index < remaining % len(row))
                if apply:
                    item.setGeometry(QRect(x, y, width, height))
                x += width + spacing
            y += height + spacing
        return y - area.y() - (spacing if rows else 0) + margins.top() + margins.bottom()
