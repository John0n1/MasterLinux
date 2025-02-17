import os
from PyQt6.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QFileDialog, QGroupBox, QFormLayout, QListView, QComboBox, 
                             QSpinBox, QCheckBox, QMessageBox)

class PreseedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preseed Options")
        self.preseed_file_path = QLineEdit()
        self.preseed_file_path.setPlaceholderText("Path to preseed file")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_preseed_file)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Preseed File:"))
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.preseed_file_path)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        self.setLayout(layout)

    def browse_preseed_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Preseed File", "", "All Files (*)")
        if file_path:
            self.preseed_file_path.setText(file_path)

    def get_preseed_file_path(self):
        return self.preseed_file_path.text()

class KernelSelectionDialog(QDialog):
    def __init__(self, available_kernels, current_kernel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kernel Selection")
        self.kernel_list = QListView()
        self.kernel_list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        # ...existing code for setting the kernel list model...
        from package_models import PackageListModel  # delayed import
        self.kernel_model = PackageListModel(available_kernels)
        self.kernel_list.setModel(self.kernel_model)
        layout = QFormLayout()
        layout.addRow("Available Kernels:", self.kernel_list)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)
        self.setLayout(layout)

    def get_selected_kernel(self):
        selected_indexes = self.kernel_list.selectedIndexes()
        if selected_indexes:
            return self.kernel_model._package_data[selected_indexes[0].row()]['name']
        return None

class AdvancedCompressionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Compression Options")
        self.compression_method_combo = QComboBox()
        self.compression_method_combo.addItems(["gzip", "xz", "bzip2", "lzma", "Custom"])
        self.compression_method_combo.currentIndexChanged.connect(self.toggle_custom_options)
        self.custom_options_group = QGroupBox("Custom Options")
        self.custom_command = QLineEdit()
        self.custom_command.setPlaceholderText("e.g., xz -9 --threads=0")
        custom_layout = QVBoxLayout()
        custom_layout.addWidget(QLabel("Custom Command:"))
        custom_layout.addWidget(self.custom_command)
        self.custom_options_group.setLayout(custom_layout)
        self.custom_options_group.hide()
        self.level_spinbox = QSpinBox()
        self.level_spinbox.setRange(0, 9)
        self.level_spinbox.setValue(6)
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(0, os.cpu_count())
        self.threads_spinbox.setValue(0)
        self.threads_spinbox.setToolTip("0 = All available cores")
        layout = QFormLayout()
        layout.addRow("Compression Method:", self.compression_method_combo)
        layout.addRow("Compression Level:", self.level_spinbox)
        layout.addRow("Threads", self.threads_spinbox)
        layout.addRow(self.custom_options_group)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)
        self.setLayout(layout)

    def toggle_custom_options(self):
        if self.compression_method_combo.currentText() == "Custom":
            self.custom_options_group.show()
        else:
            self.custom_options_group.hide()

    def get_compression_options(self):
        method = self.compression_method_combo.currentText()
        level = self.level_spinbox.value()
        threads = self.threads_spinbox.value()
        custom_command = self.custom_command.text() if method == "Custom" else ""
        return {
            "method": method,
            "level": level,
            "threads": threads,
            "custom_command": custom_command,
        }
