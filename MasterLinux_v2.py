# threads.py
# threads.py
from PyQt6.QtCore import QThread, pyqtSignal
import subprocess

class CommandRunnerThread(QThread):
    command_output_signal = pyqtSignal(str)
    command_finished_signal = pyqtSignal(int)

    def __init__(self, command, working_dir=None, chroot_path=None, is_dpkg_command=False):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.chroot_path = chroot_path
        self.is_running = True
        self.is_dpkg_command = is_dpkg_command

    def run(self):
        process = None
        try:
            if self.chroot_path:
                if isinstance(self.command, str):
                    command_list = self.command.split()
                else:
                    command_list = self.command

                if self.is_dpkg_command:
                    final_command = ["chroot", self.chroot_path] + command_list
                else:
                    final_command = ["chroot", self.chroot_path] + ["/bin/bash", "-c"] + [' '.join(command_list)]
            else:
                final_command = self.command

            if isinstance(final_command, str):
                final_command = final_command.split()

            process = subprocess.Popen(final_command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       cwd=self.working_dir,
                                       bufsize=1,
                                       universal_newlines=True)

            while self.is_running:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    self.command_output_signal.emit(output_line)

            stdout, stderr = process.communicate()
            if stdout:
                self.command_output_signal.emit(stdout)
            if stderr:
                self.command_output_signal.emit(stderr)

            self.command_finished_signal.emit(process.returncode)

        except FileNotFoundError as e:
            self.command_output_signal.emit(f"Error: Command not found: {e}\n")
            self.command_finished_signal.emit(-1)

        except Exception as e:
            self.command_output_signal.emit(f"Error executing command: {e}\n")
            self.command_finished_signal.emit(-1)

    def stop_thread(self):
        self.is_running = False

# package_models.py
from PyQt6.QtCore import QModelIndex, QAbstractTableModel, Qt, QSortFilterProxyModel
from PyQt6.QtWidgets import QApplication

class PackageListModel(QAbstractTableModel):
    def __init__(self, package_data=None):
        super().__init__()
        self._package_data = package_data if package_data else []
        self._headers = ["Remove", "Package Name", "Version"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._package_data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1:
                return self._package_data[row].get('name', '')
            elif col == 2:
                return self._package_data[row].get('version', '')
        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:
                return Qt.CheckState.Checked if self._package_data[row].get('remove') else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.BackgroundRole:
            status = self._package_data[row].get('status')
            if status == 'removing':
                return QApplication.palette().color(QApplication.palette().ColorRole.Mid)
            elif status == 'removed':
                return QApplication.palette().color(QApplication.palette().ColorRole.Highlight)
            elif status == 'error':
                return QApplication.palette().color(QApplication.palette().ColorRole.Window)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        if index.column() == 0:
            return Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            self._package_data[index.row()]['remove'] = (value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        return False

    def get_checked_packages(self):
        return [pkg['name'] for pkg in self._package_data if pkg.get('remove')]

    def set_package_status(self, package_name, status):
        for row in range(len(self._package_data)):
            if self._package_data[row]['name'] == package_name:
                self._package_data[row]['status'] = status

    def clear_package_statuses(self):
        for pkg in self._package_data:
            if 'status' in pkg:
                pkg.pop('status')

class PackageSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_text = ""

    def setFilterText(self, text):
        self.filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.filter_text:
            return True

        model = self.sourceModel()
        package_name = model._package_data[source_row]['name']
        package_version = model._package_data[source_row]['version']
        return (self.filter_text in package_name.lower() or
                self.filter_text in package_version.lower())

# dialogs.py
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QGroupBox, QListView
from PyQt6.QtWidgets import QFileDialog

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

# widgets.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QStyledItemDelegate, QStyleOptionButton

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

class CenteredIconDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 0:
            checkbox_rect = option.rect.adjusted(0, 0, -option.rect.width() + option.rect.height(), 0)
            checkbox_rect.moveCenter(option.rect.center())

            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                state = Qt.CheckState.Checked
            else:
                state = Qt.CheckState.Unchecked

            opt = QStyleOptionButton()
            opt.rect = checkbox_rect
            opt.state = state
            opt.palette = option.palette
            opt.features = QStyleOptionButton.ButtonFeature.AutoDefaultButton
            opt.ButtonType = QStyleOptionButton.ButtonType.CheckBox

            option.style().drawControl(option.style().ControlElement.CE_CheckBox, opt, painter)

        else:
            super().paint(painter, option, index)

# main.py
import os
import sys
import subprocess
import shutil
import platform
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QGroupBox, QVBoxLayout, QHBoxLayout,
                             QFormLayout, QProgressBar, QPlainTextEdit, QCheckBox,
                             QMessageBox, QTableView, QTabWidget,
                             QHeaderView, QStackedWidget, QComboBox)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QTextCursor
from PyQt6.QtCore import Qt


class ISOMasterBuilderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ISO Master Builder")
        self.setWindowIcon(QIcon.fromTheme("applications-system"))
        self.setGeometry(100, 100, 850, 700)
        self.setMinimumSize(850, 700)

        self.working_folder_path = QLineEdit()
        self.iso_file_path = QLineEdit()
        self.extracted_iso_path = ""
        self.output_iso_path = ElidedLabel()
        self.output_iso_path.setToolTip("Full path will be shown here")

        self.iso_name_edit = QLineEdit()
        self.iso_version_edit = QLineEdit()
        self.iso_architecture_edit = QLineEdit()
        self.boot_logo_path = ""
        self.preseed_file = ""

        self.step3_progress_label = QLabel("Extraction Progress:")
        self.step3_progress_bar = QProgressBar()
        self.step3_progress_bar.setRange(0, 100)
        self.step3_progress_bar.setValue(0)

        self.step7_boot_group = QGroupBox("Step 7: Re-create ISO")
        self.step7_progress_bar = QProgressBar()
        self.step7_progress_bar.setRange(0, 100)
        self.step7_progress_bar.setValue(0)
        self.step7_log_display = QPlainTextEdit()
        self.step7_log_display.setReadOnly(True)
        self.step7_log_display.setFont(QFont("Courier New", 10))

        self.step8_group = QGroupBox("Step 8: Finished")
        self.step8_summary_label = QLabel("")
        self.step8_output_path_display = QLabel("")
        self.step8_delete_temp_checkbox = QCheckBox("Delete temporary files")

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.go_to_next_step)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_to_previous_step)

        self.preseed_button = QPushButton("Preseed Options...")
        self.preseed_button.clicked.connect(self.show_preseed_dialog)

        self.kernel_button = QPushButton("Select Kernel...")
        self.kernel_button.clicked.connect(self.show_kernel_selection)

        self.advanced_compression_button = QPushButton("Advanced Compression...")
        self.advanced_compression_button.clicked.connect(self.show_advanced_compression_dialog)
        self.compression_options = {}

        self._init_ui()
        self._init_step_visibility()
        self.current_step = 1

    def _init_ui(self):
        step1_group = QGroupBox("Step 1: Working Folder")
        step1_layout = QVBoxLayout()
        working_folder_layout = QHBoxLayout()
        working_folder_layout.addWidget(QLabel("Working Folder:"))
        working_folder_layout.addWidget(self.working_folder_path)
        working_folder_layout.addWidget(QPushButton("Browse", clicked=self.browse_working_folder))
        step1_layout.addLayout(working_folder_layout)
        step1_group.setLayout(step1_layout)

        iso_file_group = QGroupBox("Step 2: ISO File Selection")
        iso_file_layout = QHBoxLayout()
        iso_file_layout.addWidget(QLabel("ISO File:"))
        self.iso_file_line = QLineEdit()
        iso_file_layout.addWidget(self.iso_file_line)
        iso_file_layout.addWidget(QPushButton("Browse", clicked=self.browse_iso_file))
        iso_file_group.setLayout(iso_file_layout)

        self.step3_group = QGroupBox("Step 3: ISO Extraction")
        step3_layout = QVBoxLayout()
        step3_layout.addWidget(self.step3_progress_label)
        step3_layout.addWidget(self.step3_progress_bar)
        self.step3_group.setLayout(step3_layout)

        self.step4_group = QGroupBox("Step 4: Customize System Configuration")
        step4_layout = QVBoxLayout()
        step4_instruction_label = QLabel("Configure your custom ISO using the tabs below:")
        step4_layout.addWidget(step4_instruction_label)

        self.step4_tab_widget = QTabWidget()

        self.step4_base_tab = QWidget()
        base_tab_layout = QFormLayout()
        self.step4_arch_combo = QComboBox()
        self.step4_arch_combo.addItems(["amd64", "i386", "arm64"])
        base_tab_layout.addRow("Architecture:", self.step4_arch_combo)
        self.step4_variant_combo = QComboBox()
        self.step4_variant_combo.addItems(["minbase", "standard"])
        base_tab_layout.addRow("Variant:", self.step4_variant_combo)
        self.step4_release_combo = QComboBox()
        self.step4_release_combo.addItems(["noble", "jammy", "focal", "bionic"])
        base_tab_layout.addRow("Release:", self.step4_release_combo)
        self.step4_mirror_line_edit = QLineEdit("http://us.archive.ubuntu.com/ubuntu/")
        base_tab_layout.addRow("Mirror:", self.step4_mirror_line_edit)
        self.step4_base_tab.setLayout(base_tab_layout)
        self.step4_tab_widget.addTab(self.step4_base_tab, "Base System")

        self.step4_packages_tab = QWidget()
        packages_tab_layout = QVBoxLayout()

        step4_removal_group = QGroupBox("Packages to Remove")
        step4_removal_layout = QVBoxLayout()
        self.step4_removal_search_line_edit = QLineEdit()
        self.step4_removal_search_line_edit.setPlaceholderText("Search packages to remove...")
        step4_removal_layout.addWidget(self.step4_removal_search_line_edit)
        self.step4_removal_package_table_view = QTableView()
        step4_removal_layout.addWidget(self.step4_removal_package_table_view)
        step4_removal_group.setLayout(step4_removal_layout)

        packages_sub_tab_widget = QTabWidget()

        self.step4_base_packages_sub_tab = QWidget()
        base_packages_sub_tab_layout = QVBoxLayout()
        self.step4_base_packages_checkbox = QCheckBox("Include standard live system packages (casper, ubiquity, etc.)")
        self.step4_base_packages_checkbox.setChecked(True)
        base_packages_sub_tab_layout.addWidget(self.step4_base_packages_checkbox)
        self.step4_base_packages_sub_tab.setLayout(base_packages_sub_tab_layout)
        packages_sub_tab_widget.addTab(self.step4_base_packages_sub_tab, "Base Packages")

        self.step4_desktop_env_sub_tab = QWidget()
        desktop_env_sub_tab_layout = QVBoxLayout()
        self.step4_desktop_env_combo = QComboBox()
        self.step4_desktop_env_combo.addItem("None")
        self.step4_desktop_env_combo.addItem("GNOME")
        desktop_env_sub_tab_layout.addWidget(QLabel("Desktop Environment:"))
        desktop_env_sub_tab_layout.addWidget(self.step4_desktop_env_combo)
        self.step4_desktop_env_sub_tab.setLayout(desktop_env_sub_tab_layout)
        packages_sub_tab_widget.addTab(self.step4_desktop_env_sub_tab, "Desktop Environment")

        self.step4_applications_sub_tab = QWidget()
        applications_sub_tab_layout = QVBoxLayout()
        self.step4_applications_search_line_edit = QLineEdit()
        self.step4_applications_search_line_edit.setPlaceholderText("Search for applications to add...")
        applications_sub_tab_layout.addWidget(self.step4_applications_search_line_edit)
        self.step4_applications_package_table_view = QTableView()
        applications_sub_tab_layout.addWidget(self.step4_applications_package_table_view)
        self.step4_applications_sub_tab.setLayout(applications_sub_tab_layout)
        packages_sub_tab_widget.addTab(self.step4_applications_sub_tab, "Applications to Add")

        packages_sub_tab_widget.addTab(step4_removal_group, "Packages to Remove")

        packages_tab_layout.addWidget(packages_sub_tab_widget)
        self.step4_packages_tab.setLayout(packages_tab_layout)
        self.step4_tab_widget.addTab(self.step4_packages_tab, "Packages")

        self.step4_settings_tab = QWidget()
        settings_tab_layout = QFormLayout()
        self.step4_hostname_line_edit = QLineEdit("ubuntu-custom")
        settings_tab_layout.addRow("Hostname:", self.step4_hostname_line_edit)
        self.step4_locales_combo = QComboBox()
        self.step4_locales_combo.addItems(["en_US.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"])
        settings_tab_layout.addRow("Default Locale:", self.step4_locales_combo)
        self.step4_upgrade_packages_checkbox = QCheckBox("Upgrade existing packages in chroot")
        self.step4_upgrade_packages_checkbox.setChecked(False)
        settings_tab_layout.addRow("Upgrade Packages:", self.step4_upgrade_packages_checkbox)
        self.step4_autoremove_checkbox = QCheckBox("Run apt autoremove to clean up")
        self.step4_autoremove_checkbox.setChecked(True)
        settings_tab_layout.addRow("Run apt autoremove:", self.step4_autoremove_checkbox)
        self.step4_settings_tab.setLayout(settings_tab_layout)
        self.step4_tab_widget.addTab(self.step4_settings_tab, "System Settings")

        step4_layout.addWidget(self.step4_tab_widget)

        step4_apply_button_layout = QHBoxLayout()
        self.step4_apply_changes_button = QPushButton("Apply Configuration Changes")
        self.step4_apply_changes_button.clicked.connect(self._apply_package_changes)
        step4_apply_button_layout.addWidget(self.step4_apply_changes_button)
        step4_layout.addLayout(step4_apply_button_layout)

        self.step4_group.setLayout(step4_layout)

        self.step7_boot_group = QGroupBox("Step 7: Re-create ISO")
        step7_layout = QVBoxLayout()
        output_iso_path_layout = QHBoxLayout()
        output_iso_path_layout.addWidget(QLabel("Output ISO:"))
        output_iso_path_layout.addWidget(self.output_iso_path)
        output_iso_path_layout.addWidget(
            QPushButton("Browse", clicked=self.browse_output_iso_location))
        step7_layout.addLayout(output_iso_path_layout)
        step7_layout.addWidget(self.preseed_button)
        step7_layout.addWidget(self.kernel_button)
        step7_layout.addWidget(self.advanced_compression_button)
        step7_layout.addWidget(self.step7_progress_bar)
        step7_layout.addWidget(self.step7_log_display)

        self.step7_boot_group.setLayout(step7_layout)

        self.step8_group = QGroupBox("Step 8: Finished")
        step8_layout = QVBoxLayout()
        step8_layout.addWidget(self.step8_summary_label)
        step8_layout.addWidget(self.step8_output_path_display)
        step8_layout.addWidget(QPushButton("Open Output Folder", clicked=self._open_output_folder))
        step8_layout.addWidget(self.step8_delete_temp_checkbox)
        step8_layout.addStretch(1)
        self.step8_group.setLayout(step8_layout)

        self.stack = QStackedWidget()
        self.stack.addWidget(step1_group)
        self.stack.addWidget(iso_file_group)
        self.stack.addWidget(self.step3_group)
        self.stack.addWidget(self.step4_group)
        self.stack.addWidget(self.step7_boot_group)
        self.stack.addWidget(self.step8_group)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.next_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        self.back_button.hide()

    def _init_step_visibility(self):
        self.step3_group.hide()
        self.step4_group.hide()
        self.step7_boot_group.hide()
        self.step8_group.hide()

        self.step7_progress_bar.hide()
        self.step7_log_display.hide()

    def show_preseed_dialog(self):
        dialog = PreseedDialog(self)
        if dialog.exec():
            self.preseed_file = dialog.get_preseed_file_path()
            if self.preseed_file:
                print(f"Preseed file selected: {self.preseed_file}")

    def show_kernel_selection(self):
        if not self.extracted_iso_path or not os.path.exists(self.extracted_iso_path):
            QMessageBox.warning(self, "Warning", "ISO must be extracted before selecting a kernel.")
            return

        command = ["chroot", self.extracted_iso_path, "apt-get", "list", "--installed", "linux-image-*"]
        try:

            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output_lines = result.stdout.strip().split('\n')
            available_kernels = []
            current_kernel = ""

            for line in output_lines:
                if "linux-image-" in line and "installed" in line:
                    parts = line.split()
                    kernel_name_parts = parts[0].split("/")
                    kernel_name = kernel_name_parts[0] if kernel_name_parts else "Unknown"
                    version_part = parts[1].split(",")
                    version = version_part[0] if version_part else "Unknown"
                    available_kernels.append({'name': kernel_name, 'version': version, 'remove': False})

            if not available_kernels:
                QMessageBox.information(self, "Kernel Selection", "No alternative kernels found.")
                return

            dialog = KernelSelectionDialog(available_kernels, current_kernel, self)
            if dialog.exec():
                selected_kernel = dialog.get_selected_kernel()
                if selected_kernel:
                    print(f"Selected Kernel: {selected_kernel}")

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "'chroot' or 'apt' command not found.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Error listing kernels: {e.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_advanced_compression_dialog(self):
        dialog = AdvancedCompressionDialog(self)
        if dialog.exec():
            self.compression_options = dialog.get_compression_options()
            print(f"Compression Options: {self.compression_options}")

    def browse_working_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Working Folder")
        if folder_path:
            self.working_folder_path.setText(folder_path)
            print(f"Working folder selected: {folder_path}")

    def browse_iso_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ISO File", "", "ISO Files (*.iso)")
        if file_path:
            if not os.path.exists(file_path):
                QMessageBox.critical(self, "Error", "Selected ISO file does not exist.")
                return
            self.iso_file_line.setText(file_path)
            self.iso_file_path.setText(file_path)
            print(f"ISO file selected: {file_path}")
            self._populate_iso_info()

    def browse_output_iso_location(self):
        default_filename = f"custom-{os.path.basename(self.iso_file_path.text())}"
        default_path = os.path.join(os.path.dirname(self.iso_file_path.text()), default_filename)

        file_path, _ = QFileDialog.getSaveFileName(self, "Save ISO As", default_path, "ISO Files (*.iso)")
        if file_path:
            if not file_path.lower().endswith(".iso"):
                file_path += ".iso"
            self.output_iso_path.setText(file_path)
            self.output_iso_path.setToolTip(file_path)
            print(f"Output ISO path selected: {file_path}")

    def _populate_iso_info(self):
        if not self.iso_file_path.text():
            return

        try:
            iso_path = self.iso_file_path.text()
            cmd = ["xorriso", "-indev", iso_path, "-report_system_area", "as_mkisofs"]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output_lines = process.stdout.strip().split('\n')
            iso_name = "Unknown"
            iso_version = "Unknown"
            iso_architecture = "Unknown"

            for line in output_lines:
                if line.startswith("System_ID="):
                    iso_name = line.split("=")[1].strip("'")
                elif line.startswith("Application_ID="):
                    iso_version = line.split("=")[1].strip("'")

            filename = os.path.basename(iso_path).lower()
            if "amd64" in filename:
                iso_architecture = "amd64"
            elif "i386" in filename:
                iso_architecture = "i386"
            elif "arm64" in filename:
                iso_architecture = "arm64"

            self.iso_name_edit.setText(iso_name)
            self.iso_version_edit.setText(iso_version)
            self.iso_architecture_edit.setText(iso_architecture)
            print("ISO information extracted.")

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "xorriso command not found. Is it installed?")
            print("Error: xorriso not found.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Error extracting ISO info with xorriso: {e.stderr}")
            print(f"Error running xorriso: {e.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred during ISO info extraction: {e}")
            print(f"Unexpected error during ISO info extraction: {e}")

    def go_to_next_step(self):
        if self.current_step == 1:
            if not self.working_folder_path.text():
                QMessageBox.warning(self, "Warning", "Please select working folder")
                return
            self.go_to_step(2)
        elif self.current_step == 2:
            self.go_to_step(3)
        elif self.current_step == 3:
            self.go_to_step(4)
        elif self.current_step == 4:
            if self.modification_thread and self.modification_thread.isRunning():
                QMessageBox.warning(self, "Warning", "Package modifications are still in progress. Please wait until they are finished.")
                return
            self.go_to_step(7)
        elif self.current_step == 7:
            self._start_iso_recreation()
        elif self.current_step == 8:
            if self.step8_delete_temp_checkbox.isChecked():
                self.delete_temp_files()
            QApplication.quit()

    def go_to_previous_step(self):
        if self.current_step > 1 and self.current_step != 5 and self.current_step != 6:
            self.go_to_step(self.current_step - 1)
        elif self.current_step == 7:
            self.go_to_step(4)

    def go_to_step(self, step_number):
        self.stack.setCurrentIndex(step_number - 1)
        self.current_step = step_number

        if self.current_step == 3:
            self._extract_iso()
        elif self.current_step == 4:
            self._populate_package_lists_for_checklist()

        self.back_button.setEnabled(self.current_step > 1)
        if self.current_step == self.stack.count():
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Next")

    def _extract_iso(self):
        working_folder = self.working_folder_path.text()
        iso_file = self.iso_file_path.text()
        self.extracted_iso_path = os.path.join(working_folder, "extracted_iso")
        os.makedirs(self.extracted_iso_path, exist_ok=True)

        self.step3_progress_bar.setValue(0)
        self.step3_progress_bar.setFormat("%p% - Extracting...")

        try:
            iso_file = self.iso_file_path.text()
            cmd = ["xorriso", "-osirrox", "on", "-indev", iso_file, "-extract", "/", self.extracted_iso_path]

            self.extraction_thread = CommandRunnerThread(cmd)
            self.extraction_thread.command_output_signal.connect(self._process_extraction_output)
            self.extraction_thread.command_finished_signal.connect(self._extraction_finished)
            self.extraction_thread.start()

        except FileNotFoundError:
            self.step3_progress_bar.setFormat("Error")
            QMessageBox.critical(self, "Error", "xorriso command not found. Is it installed?")
            print("Error: xorriso not found.")
        except Exception as e:
            self.step3_progress_bar.setFormat("Error")
            QMessageBox.critical(self, "Error", f"Unexpected error during ISO extraction: {e}")
            print(f"Unexpected error during ISO extraction: {e}")

    def _process_extraction_output(self, output_text):
        if "filesினாலும்" in output_text:
            try:
                parts = output_text.split("filesினாலும்")
                numbers = parts[0].split()
                current = int(numbers[-2].strip())
                total = int(numbers[-1].strip())
                percent = int((current / total) * 100)
                self.step3_progress_bar.setValue(percent)

            except (ValueError, IndexError):
                pass

    def _extraction_finished(self, return_code):
        if return_code == 0:
            self.step3_progress_bar.setValue(100)
            self.step3_progress_bar.setFormat("%p% - Extraction Complete")
            print("ISO extraction completed.")
            self.back_button.setEnabled(True)
            self.next_button.setEnabled(True)

        else:
            self.step3_progress_bar.setFormat("Extraction Failed")
            QMessageBox.critical(self, "Error", "ISO extraction failed.")
            print("Error during ISO extraction.")
            self.back_button.setEnabled(True)

    def browse_boot_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Boot Logo Image", "",
                                                   "Images (*.png *.jpg *.bmp *.svg *.xpm)")
        if file_path:
            self.boot_logo_path = file_path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 50, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
            else:
                pass
            print(f"Boot logo selected: {file_path}")

    def _fetch_installed_packages(self):
        command = ["apt-get", "list", "--installed"]
        chroot_command = ["chroot", self.extracted_iso_path] + command
        try:
            result = subprocess.run(chroot_command, capture_output=True, text=True, check=True)
            output_text = result.stdout
            lines = output_text.strip().split('\n')
            package_data = []
            for line in lines:
                if "/" in line and ",now" in line:
                    parts = line.split()
                    package_name_parts = parts[0].split("/")
                    package_name = package_name_parts[0]
                    version_part = parts[1].split(",")
                    version = version_part[0]
                    package_data.append({'name': package_name, 'version': version, 'remove': False})
            return package_data
        except subprocess.CalledProcessError as e:
            print(f"Error fetching installed packages: {e.stderr}")
            QMessageBox.critical(self, "Error", f"Error fetching installed packages: {e.stderr}")
            return []
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "'apt' command not found in system or chroot environment.")
            return []

    def _fetch_available_packages(self):
        command = ["apt-get", "list"]
        chroot_command = ["chroot", self.extracted_iso_path] + command
        try:
            result = subprocess.run(chroot_command, capture_output=True, text=True, check=True)
            output_text = result.stdout
            lines = output_text.strip().split('\n')
            package_data = []
            for line in lines:
                if "/" in line and not line.startswith("Listing..."):
                    parts = line.split()
                    package_name_parts = parts[0].split("/")
                    package_name = package_name_parts[0]
                    version_part = parts[1].split(",")
                    version = version_part[0] if version_part else "Unknown"
                    package_data.append({'name': package_name, 'version': version, 'remove': False})
            return package_data
        except subprocess.CalledProcessError as e:
            print(f"Error fetching available packages: {e.stderr}")
            QMessageBox.critical(self, "Error", f"Error fetching available packages: {e.stderr}")
            return []
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "'apt' command not found in system or chroot environment.")
            return []

    def _populate_package_lists_for_checklist(self):
        print("Populating package lists for Step 4 checklist...")

        installed_packages_data = self._fetch_installed_packages()
        self.step4_removal_package_model = PackageListModel(installed_packages_data)
        self.step4_removal_proxy_model = PackageSortFilterProxyModel()
        self.step4_removal_proxy_model.setSourceModel(self.step4_removal_package_model)
        self.step4_removal_package_table_view.setModel(self.step4_removal_proxy_model)
        self.step4_removal_package_table_view.setItemDelegate(CenteredIconDelegate())
        self.step4_removal_package_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.step4_removal_package_table_view.setSortingEnabled(True)
        self.step4_removal_search_line_edit.textChanged.connect(self._filter_removal_package_list)

        available_packages_data = self._fetch_available_packages()
        self.step4_addition_package_model = PackageListModel(available_packages_data)
        self.step4_addition_proxy_model = PackageSortFilterProxyModel()
        self.step4_addition_proxy_model.setSourceModel(self.step4_addition_package_model)
        self.step4_addition_package_table_view.setModel(self.step4_addition_proxy_model)
        self.step4_addition_package_table_view.setItemDelegate(CenteredIconDelegate())
        self.step4_addition_package_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.step4_addition_package_table_view.setSortingEnabled(True)
        self.step4_applications_search_line_edit.textChanged.connect(self._filter_addition_package_list)

        print("Package lists populated.")

    def _filter_removal_package_list(self, filter_text):
        self.step4_removal_proxy_model.setFilterText(filter_text)

    def _filter_addition_package_list(self, filter_text):
        self.step4_addition_proxy_model.setFilterText(filter_text)

    def _apply_package_changes(self):
        commands = []

        arch = self.step4_arch_combo.currentText()
        variant = self.step4_variant_combo.currentText()
        release = self.step4_release_combo.currentText()
        mirror = self.step4_mirror_line_edit.text()

        debootstrap_command = [
            "debootstrap",
            "--arch", arch,
            "--variant", variant,
            release,
            self.extracted_iso_path,
            mirror
        ]
        commands.append(("Bootstrap Base System", debootstrap_command))

        if self.step4_base_packages_checkbox.isChecked():
            base_packages_command = [
                "apt-get", "install", "-y", "--force-yes", "--allow-unauthenticated",
                "ubuntu-standard",
                "casper",
                "discover",
                "laptop-detect",
                "os-prober",
                "network-manager",
                "net-tools",
                "wireless-tools",
                "wpagui",
                "locales",
                "grub-common",
                "grub-gfxpayload-lists",
                "grub-pc",
                "grub-pc-bin",
                "grub2-common",
                "grub-efi-amd64-signed",
                "shim-signed",
                "mtools",
                "binutils",
                "ubiquity",
                "ubiquity-casper",
                "ubiquity-frontend-gtk",
                "ubiquity-slideshow-ubuntu",
                "ubiquity-ubuntu-artwork"
            ]
            commands.append(("Install Base Packages", base_packages_command))

        desktop_env = self.step4_desktop_env_combo.currentText()
        if desktop_env == "GNOME":
            desktop_packages_command = [
                "apt-get", "install", "-y", "--no-install-recommends",
                "plymouth-themes",
                "ubuntu-gnome-desktop",
                "ubuntu-gnome-wallpapers"
            ]
            commands.append(("Install GNOME Desktop", desktop_packages_command))

        applications_to_add = self.step4_addition_package_model.get_checked_packages()
        if applications_to_add:
            install_apps_command = ["apt-get", "install", "-y"] + applications_to_add
            commands.append(("Install Applications", install_apps_command))

        packages_to_remove = self.step4_removal_package_model.get_checked_packages()
        if packages_to_remove:
            remove_packages_command = ["apt-get", "purge", "-y"] + packages_to_remove
            commands.append(("Remove Packages", remove_packages_command))

        hostname = self.step4_hostname_line_edit.text()
        locale = self.step4_locales_combo.currentText()
        upgrade_packages = self.step4_upgrade_packages_checkbox.isChecked()
        autoremove = self.step4_autoremove_checkbox.isChecked()

        if hostname:
            set_hostname_command = ["/bin/bash", "-c", f"echo '{hostname}' > /etc/hostname"]
            commands.append(("Set Hostname", set_hostname_command))

        if locale:
            reconfigure_locales_command = ["dpkg-reconfigure", "locales"]
            commands.append(("Reconfigure Locales", reconfigure_locales_command))

        if upgrade_packages:
            upgrade_command = ["apt-get", "upgrade", "-y"]
            commands.append(("Upgrade Packages", upgrade_command))

        if autoremove:
            autoremove_command = ["apt-get", "autoremove", "-y"]
            commands.append(("Run apt Autoremove", autoremove_command))

        if not commands:
            QMessageBox.information(self, "Information", "No configuration changes selected.")
            return

        confirmation_message = "Confirm system configuration changes:\n\nActions to be performed:\n"
        for op_name, _ in commands:
            confirmation_message += f"- {op_name}\n"

        reply = QMessageBox.question(self, 'Confirm Changes',
                                     confirmation_message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self._execute_package_modifications(commands)

    def _execute_package_modifications(self, commands):
        if not commands:
            return

        self.step4_progress_bar = QProgressBar()
        self.step4_progress_bar.setRange(0, len(commands))
        self.step4_progress_bar.setValue(0)
        self.step4_progress_label = QLabel("Applying Configuration Changes:")
        self.step4_log_display = QPlainTextEdit()
        self.step4_log_display.setReadOnly(True)
        self.step4_log_display.setFont(QFont("Courier New", 10))

        step4_layout = self.step4_group.layout()
        step4_layout.addWidget(self.step4_progress_label)
        step4_layout.addWidget(self.step4_progress_bar)
        step4_layout.addWidget(self.step4_log_display)
        self.step4_progress_label.show()
        self.step4_progress_bar.show()
        self.step4_log_display.show()

        self.current_modification_command_index = 0
        self.modification_commands = commands
        self._execute_next_modification_command()

    def _execute_next_modification_command(self):
        if self.current_modification_command_index >= len(self.modification_commands):
            self._package_modifications_finished()
            return

        operation_name, command = self.modification_commands[self.current_modification_command_index]
        self.step4_progress_label.setText(f"Applying Changes: {operation_name}...")

        use_chroot = operation_name not in ["Bootstrap Base System"]
        chroot_path_val = self.extracted_iso_path if use_chroot else None
        is_dpkg_command_val = use_chroot

        self.modification_thread = CommandRunnerThread(command, chroot_path=chroot_path_val, is_dpkg_command=is_dpkg_command_val)
        self.modification_thread.command_output_signal.connect(self._process_modification_output)
        self.modification_thread.command_finished_signal.connect(self._handle_modification_command_finished)
        self.modification_thread.start()

    def _handle_modification_command_finished(self, return_code):
        if return_code == 0:
            print(f"Package modification command finished successfully.")
        else:
            QMessageBox.warning(self, "Warning", f"Package modification command failed with return code: {return_code}")

        self.current_modification_command_index += 1
        self.step4_progress_bar.setValue(self.current_modification_command_index)
        self._execute_next_modification_command()

    def _process_modification_output(self, output_text):
        self.step4_log_display.moveCursor(QTextCursor.MoveOperation.End)
        self.step4_log_display.insertPlainText(output_text)
        self.step4_log_display.moveCursor(QTextCursor.MoveOperation.End)

    def _package_modifications_finished(self):
        self.modification_thread = None
        self.step4_progress_label.setText("Configuration Changes Applied.")
        QMessageBox.information(self, "Success", "System configuration changes have been applied.")

        print("System configuration modifications finished.")

    def _start_iso_recreation(self):
        output_iso_file = self.output_iso_path.text()

        if not output_iso_file:
            QMessageBox.warning(self, "Warning", "Please specify output ISO path.")
            return
        if not self.compression_options:
            self.compression_options = {"method": "gzip", "level": 6, "threads": 0, "custom_command": ""}

        self.step7_log_display.clear()
        self.step7_progress_bar.setValue(0)
        self.step7_progress_bar.show()
        self.step7_log_display.show()
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)

        cmd = [
            "xorriso",
            "-as", "mkisofs",
            "-r",
            "-J",
            "-joliet-long",
            "-l",
            "-cache-inodes",
            "-follow-links",
            "-o", output_iso_file,
            "-b", "isolinux/isolinux.bin",
            "-c", "isolinux/boot.cat",
            "-no-emul-boot",
            "-boot-load-size", "4",
            "-boot-info-table",
            "-isohybrid-mbr", "isolinux/isohdpfx.bin",
            "-eltorito-alt-boot",
            "-e", "boot/grub/efi.img",
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
        ]

        if self.preseed_file and os.path.exists(self.preseed_file):
            cmd.extend(["-preseed", self.preseed_file])

        if self.boot_logo_path and os.path.exists(self.boot_logo_path):
            isolinux_dir = os.path.join(self.extracted_iso_path, "isolinux")
            if not os.path.exists(isolinux_dir):
                os.makedirs(isolinux_dir)

            logo_dest_path = os.path.join(isolinux_dir, "logo.png")
            try:
                shutil.copy(self.boot_logo_path, logo_dest_path)

                cfg_path = os.path.join(isolinux_dir, "isolinux.cfg")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "a") as cfg_file:
                        cfg_file.write(f"\nUI vesamenu.c32\nMENU BACKGROUND logo.png\n")
            except (shutil.Error, IOError) as e:
                QMessageBox.warning(self, "Warning", f"Failed to copy boot logo: {e}")

        cmd.append(self.extracted_iso_path)

        self.iso_recreation_thread = CommandRunnerThread(cmd,
                                                        working_dir=self.working_folder_path.text())
        self.iso_recreation_thread.command_output_signal.connect(self._process_iso_recreation_output)
        self.iso_recreation_thread.command_finished_signal.connect(self._iso_recreation_finished)
        self.iso_recreation_thread.start()

    def _process_iso_recreation_output(self, output_text):
        self.step7_log_display.moveCursor(QTextCursor.MoveOperation.End)
        self.step7_log_display.insertPlainText(output_text)
        self.step7_log_display.moveCursor(QTextCursor.MoveOperation.End)

        if "xorriso : UPDATE : " in output_text:
            try:
                parts = output_text.split(":")
                progress_part = parts[-1].strip()
                if progress_part.endswith("%"):
                    progress_percent = int(progress_part[:-1])
                    self.step7_progress_bar.setValue(progress_percent)
            except (ValueError, IndexError):
                pass

    def _iso_recreation_finished(self, return_code):
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
        if return_code == 0:
            self.step7_progress_bar.setValue(100)
        else:
            self.step7_progress_bar.setFormat("ISO Creation Failed")
            QMessageBox.critical(self, "Error", f"ISO re-creation failed with return code {return_code}.")

        self.iso_recreation_thread = None
        self.go_to_step(8)

    def _open_output_folder(self):
        output_dir = os.path.dirname(self.output_iso_path.text())
        if os.path.exists(output_dir):
            if sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', output_dir])
            elif sys.platform.startswith('win'):
                os.startfile(output_dir)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', output_dir])
            else:
                QMessageBox.warning(self, "Warning", "Cannot open output folder automatically on this platform.")
        else:
            QMessageBox.warning(self, "Warning", "Output folder does not exist.")

    def delete_temp_files(self):
        if self.extracted_iso_path and os.path.exists(self.extracted_iso_path):
            try:
                shutil.rmtree(self.extracted_iso_path)
                print(f"Deleted temporary directory: {self.extracted_iso_path}")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to delete temporary files: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ISOMasterBuilderApp()
    window.show()
    sys.exit(app.exec())