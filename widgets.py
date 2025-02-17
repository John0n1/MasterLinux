from PyQt6.QtWidgets import QLabel, QStyledItemDelegate, QCheckBox
from PyQt6.QtCore import Qt

# Custom label that handles elided text.
class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.original_text = text

    def setText(self, text):
        self.original_text = text
        super().setText(self.elide_text(self.width()))

    def elide_text(self, width):
        fm = self.fontMetrics()
        return fm.elidedText(self.original_text, Qt.TextElideMode.ElideMiddle, width)

    def resizeEvent(self, event):
        super().setText(self.elide_text(self.width()))
        super().resizeEvent(event)

# Delegate that centers a checkbox.
class CenteredIconDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 0:
            checkbox_rect = option.rect.adjusted(0, 0, -option.rect.width() + option.rect.height(), 0)
            checkbox_rect.moveCenter(option.rect.center())

            # Determine state.
            state = None
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                state = 2  # Checked placeholder
            else:
                state = 0  # Unchecked placeholder

            # Draw the checkbox.
            opt = QCheckBox()
            opt.rect = checkbox_rect
            opt.state = state
            opt.palette = option.palette
            opt.style().drawControl(opt.style().ControlElement.CE_CheckBox, opt, painter)
        else:
            super().paint(painter, option, index)
