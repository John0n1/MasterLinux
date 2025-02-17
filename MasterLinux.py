import shutil
import os, sys, subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QGroupBox, QMessageBox, QProgressBar, QPlainTextEdit, QTableView, QHeaderView, QComboBox, QCheckBox, QListView, QDialog, QFormLayout, QSpinBox, QRadioButton, QButtonGroup
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QPixmap
from PyQt6.QtCore import Qt

# Import custom modules
from widgets import ElidedLabel, CenteredIconDelegate
from threads import CommandRunnerThread
from package_models import PackageListModel, PackageSortFilterProxyModel
from dialogs import PreseedDialog, KernelSelectionDialog, AdvancedCompressionDialog

class ISOMasterBuilderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ISO Master Builder")
        self.setWindowIcon(QIcon.fromTheme("applications-system"))  # More generic icon
        self.setGeometry(100, 100, 850, 700)
        self.setMinimumSize(850, 700) # Make sure the UI doesn't become too small

        self.working_folder_path = QLineEdit()
        self.iso_file_path = QLineEdit()
        self.extracted_iso_path = ""
        self.output_iso_path = ElidedLabel()  # Use ElidedLabel
        self.output_iso_path.setToolTip("Full path will be shown here") #tooltip


        self.iso_name_edit = QLineEdit()
        self.iso_version_edit = QLineEdit()
        self.iso_architecture_edit = QLineEdit()
        self.boot_logo_path = ""
        self.preseed_file = ""


        # UI elements for steps
        self.step3_progress_label = QLabel("Extraction Progress:")
        self.step3_progress_bar = QProgressBar()
        self.step3_progress_bar.setRange(0, 100)
        self.step3_progress_bar.setValue(0)

        self.step4_terminal_label = QLabel("Customize ISO (Chroot Terminal)")
        self.step4_terminal = QPlainTextEdit()
        self.step4_terminal.setFont(QFont("Courier New", 10)) # Use Monospaced font
        self.step4_terminal.setReadOnly(False)
        self.step4_terminal.setPlainText(f"# Type 'help' for basic commands.\n\n$ ")
        self.step4_terminal_instruction = QLabel("Use the terminal below to customize your ISO (chroot environment).")
        self.step4_terminal_command_history = []
        self.step4_terminal_history_index = -1
        self.command_runner_thread = None

        self.step5_group = QGroupBox("Step 5: Package Removal")
        self.step5_search_line_edit = QLineEdit()
        self.step5_search_line_edit.setPlaceholderText("Search packages...")
        self.step5_search_line_edit.textChanged.connect(self._filter_package_list)
        self.step5_package_table_view = QTableView()
        self.step5_package_model = PackageListModel()
        self.step5_proxy_model = PackageSortFilterProxyModel()
        self.step5_proxy_model.setSourceModel(self.step5_package_model)
        self.step5_package_table_view.setModel(self.step5_proxy_model)
        self.step5_package_table_view.setItemDelegate(CenteredIconDelegate())  # Center checkboxes
        self.step5_package_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.step5_package_table_view.setSortingEnabled(True)

        self.step6_group = QGroupBox("Step 6: Confirm Package Removal")
        self.step6_progress_label = QLabel("Package Removal Progress:")
        self.step6_package_list_display = QPlainTextEdit()
        self.step6_package_list_display.setReadOnly(True)
        self.step6_package_list_display.setFont(QFont("Courier New", 10)) #monospaced
        self.step6_progress_bar = QProgressBar()  # Progress bar for removal
        self.step6_progress_bar.setRange(0, 100)
        self.step6_progress_bar.setValue(0)


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

        # Navigation buttons - using consistent naming
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.go_to_next_step)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_to_previous_step)

        # Step specific actions
        self.terminal_stop_button = QPushButton("Stop Command")
        self.terminal_stop_button.clicked.connect(self.stop_terminal_command)
        self.step5_refresh_button = QPushButton("Refresh Package List")
        self.step5_refresh_button.clicked.connect(self.refresh_package_list)

        self.step6_confirm_button = QPushButton("Confirm Removal")
        self.step6_confirm_button.clicked.connect(self.confirm_package_removal)

        # Advanced Options
        self.preseed_button = QPushButton("Preseed Options...")
        self.preseed_button.clicked.connect(self.show_preseed_dialog)

        self.kernel_button = QPushButton("Select Kernel...")
        self.kernel_button.clicked.connect(self.show_kernel_selection)

        self.advanced_compression_button = QPushButton("Advanced Compression...")
        self.advanced_compression_button.clicked.connect(self.show_advanced_compression_dialog)
        self.compression_options = {}  # Store compression options

        self._init_ui()
        self._init_step_visibility()
        self.step4_terminal.installEventFilter(self)
        self.current_step = 1  # Track the current step


    def _init_ui(self):
        # Step 1: Working Folder
        step1_group = QGroupBox("Step 1: Working Folder")
        step1_layout = QVBoxLayout()
        working_folder_layout = QHBoxLayout()
        working_folder_layout.addWidget(QLabel("Working Folder:"))
        working_folder_layout.addWidget(self.working_folder_path)
        working_folder_layout.addWidget(QPushButton("Browse", clicked=self.browse_working_folder))
        step1_layout.addLayout(working_folder_layout)
        step1_group.setLayout(step1_layout)

        # Step 2: ISO File and Information
        iso_info_group = QGroupBox("Step 2: ISO File and Information")
        iso_info_layout = QVBoxLayout()
        iso_file_layout = QHBoxLayout()
        iso_file_layout.addWidget(QLabel("ISO File:"))
        iso_file_layout.addWidget(self.iso_file_path)
        iso_file_layout.addWidget(QPushButton("Browse", clicked=self.browse_iso_file))
        iso_info_layout.addLayout(iso_file_layout)

        iso_info_grid = QFormLayout()  # Use QFormLayout for labels and fields
        iso_info_grid.addRow("ISO Name:", self.iso_name_edit)
        iso_info_grid.addRow("Version:", self.iso_version_edit)
        iso_info_grid.addRow("Architecture:", self.iso_architecture_edit)

        boot_logo_layout = QHBoxLayout()
        self.boot_logo_label = QLabel("Boot Logo:")
        self.boot_logo_preview = QLabel("No logo selected")
        self.boot_logo_button = QPushButton("Browse")
        self.boot_logo_button.clicked.connect(self.browse_boot_logo)
        boot_logo_layout.addWidget(self.boot_logo_label)
        boot_logo_layout.addWidget(self.boot_logo_preview)
        boot_logo_layout.addWidget(self.boot_logo_button)
        iso_info_grid.addRow(boot_logo_layout)


        iso_info_layout.addLayout(iso_info_grid)
        iso_info_group.setLayout(iso_info_layout)

        # Step 3: ISO Extraction
        self.step3_group = QGroupBox("Step 3: ISO Extraction")
        step3_layout = QVBoxLayout()
        step3_layout.addWidget(self.step3_progress_label)
        step3_layout.addWidget(self.step3_progress_bar)
        self.step3_group.setLayout(step3_layout)


        # Step 4: Chroot Terminal
        self.step4_group = QGroupBox("Step 4: Customize ISO (Chroot Terminal)")
        step4_layout = QVBoxLayout()
        step4_layout.addWidget(self.step4_terminal_label)
        step4_layout.addWidget(self.step4_terminal_instruction)
        step4_layout.addWidget(self.step4_terminal)
        step4_button_layout = QHBoxLayout()
        step4_button_layout.addWidget(self.terminal_stop_button)
        step4_button_layout.addStretch(1) # Push stop button to left.
        step4_layout.addLayout(step4_button_layout)
        self.step4_group.setLayout(step4_layout)


        # Step 5: Package Removal
        step5_layout = QVBoxLayout()
        step5_layout.addWidget(self.step5_search_line_edit)
        step5_layout.addWidget(self.step5_package_table_view)
        step5_button_layout = QHBoxLayout()
        step5_button_layout.addWidget(self.step5_refresh_button)
        step5_button_layout.addStretch(1)
        self.step5_group.setLayout(step5_layout)
        step5_layout.addLayout(step5_button_layout) #add button layout


        # Step 6: Confirm and Execute Package Removal
        step6_layout = QVBoxLayout()
        step6_layout.addWidget(self.step6_package_list_display)
        step6_layout.addWidget(self.step6_progress_label)
        step6_layout.addWidget(self.step6_progress_bar)  # Add progress bar
        step6_button_layout = QHBoxLayout()
        step6_button_layout.addWidget(self.step6_confirm_button)
        step6_button_layout.addStretch(1)
        self.step6_group.setLayout(step6_layout)
        step6_layout.addLayout(step6_button_layout) #Add button layout

        # Step 7: Re-create ISO
        step7_layout = QVBoxLayout()
        output_iso_path_layout = QHBoxLayout()
        output_iso_path_layout.addWidget(QLabel("Output ISO:"))
        output_iso_path_layout.addWidget(self.output_iso_path)
        output_iso_path_layout.addWidget(QPushButton("Browse", clicked=self.browse_output_iso_location)) #save as location
        step7_layout.addLayout(output_iso_path_layout)
        step7_layout.addWidget(self.preseed_button) #advanced options
        step7_layout.addWidget(self.kernel_button) #kernel
        step7_layout.addWidget(self.advanced_compression_button)  # Advanced compression
        step7_layout.addWidget(self.step7_progress_bar)
        step7_layout.addWidget(self.step7_log_display)

        self.step7_boot_group.setLayout(step7_layout)

       # Step 8: Finished
        step8_layout = QVBoxLayout()
        step8_layout.addWidget(self.step8_summary_label)
        step8_layout.addWidget(self.step8_output_path_display)
        step8_layout.addWidget(QPushButton("Open Output Folder", clicked=self._open_output_folder))
        step8_layout.addWidget(self.step8_delete_temp_checkbox)
        step8_layout.addStretch(1)
        self.step8_group.setLayout(step8_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(step1_group)
        main_layout.addWidget(iso_info_group)
        main_layout.addWidget(self.step3_group)
        main_layout.addWidget(self.step4_group)
        main_layout.addWidget(self.step5_group)
        main_layout.addWidget(self.step6_group)
        main_layout.addWidget(self.step7_boot_group)
        main_layout.addWidget(self.step8_group)

        # Navigation button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_button)
        button_layout.addStretch(1)  # Center the buttons
        button_layout.addWidget(self.next_button)
        main_layout.addLayout(button_layout)  # Add button layout to main layout

        self.setLayout(main_layout)
        self.back_button.hide()  # Hide back button initially


    def _init_step_visibility(self):
        # Hide all steps except the first one
        self.step3_group.hide()
        self.step4_group.hide()
        self.step5_group.hide()
        self.step6_group.hide()
        self.step7_boot_group.hide()
        self.step8_group.hide()

        # Hide step-specific elements initially
        self.terminal_stop_button.hide()
        self.step5_refresh_button.hide()
        self.step6_progress_label.hide()
        self.step6_progress_bar.hide()
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
        # Find available kernels in the chroot environment
        command = ["chroot", self.extracted_iso_path, "apt", "list", "--installed", "linux-image-*"]
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
                    available_kernels.append({'name': kernel_name, 'version': version, 'remove': False})  # Add 'remove' key

            if not available_kernels:
                QMessageBox.information(self, "Kernel Selection", "No alternative kernels found.")
                return

            dialog = KernelSelectionDialog(available_kernels, current_kernel, self)
            if dialog.exec():
                selected_kernel = dialog.get_selected_kernel()
                if selected_kernel:
                     print(f"Selected Kernel: {selected_kernel}")
                     #implement kernel install.

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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Base ISO File", "", "ISO Files (*.iso)")
        if file_path:
            if not os.path.exists(file_path):
                QMessageBox.critical(self, "Error", "Selected ISO file does not exist.")
                return
            self.iso_file_path.setText(file_path)
            print(f"ISO file selected: {file_path}")
            self._populate_iso_info()

    def browse_output_iso_location(self):
        default_filename = f"custom-{os.path.basename(self.iso_file_path.text())}"  # Suggest a filename
        default_path = os.path.join(os.path.dirname(self.iso_file_path.text()), default_filename) #Join dirname and filename

        file_path, _ = QFileDialog.getSaveFileName(self, "Save ISO As", default_path, "ISO Files (*.iso)")
        if file_path:
            # Ensure .iso extension
            if not file_path.lower().endswith(".iso"):
                file_path += ".iso"
            self.output_iso_path.setText(file_path)
            self.output_iso_path.setToolTip(file_path)  # Show full path in tooltip.
            print(f"Output ISO path selected: {file_path}")

    def _populate_iso_info(self):
        if not self.iso_file_path.text():
            return

        try:
            iso_path =  self.iso_file_path.text()
            cmd = ["xorriso", "-indev", iso_path, "-report_system_id", "-", "-report_application_id", "-"]
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

            # Try to get architecture from the filename (fallback)
            filename = os.path.basename(iso_path).lower()
            if "amd64" in filename:
                iso_architecture = "amd64"
            elif "i386" in filename:
                iso_architecture = "i386"
            elif "arm64" in filename:
                iso_architecture = "arm64"
            # Add more architecture checks as needed

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
            if not self.working_folder_path.text() or not self.iso_file_path.text():
                QMessageBox.warning(self, "Warning", "Please select working folder and ISO file.")
                return
            self.go_to_step(2)  # Go to step 2 (ISO Info)
        elif self.current_step == 2:
            self.go_to_step(3)  # Go to step 3 (Extraction)
        elif self.current_step == 3:
            self.go_to_step(4)  # Go to step 4 (Chroot)
        elif self.current_step == 4:
            self.go_to_step(5)  # Go to step 5 (Package List)
        elif self.current_step == 5:
            self.go_to_step(6)  # Attempt to go to step 6 (Confirm Removal)
        elif self.current_step == 6:
            self.go_to_step(7) #go to Re-create ISO
        elif self.current_step == 7:
            self._start_iso_recreation()
        elif self.current_step == 8:
            # Finish (Close Application or Restart)
            if self.step8_delete_temp_checkbox.isChecked():
                self.delete_temp_files()
            QApplication.quit()


    def go_to_previous_step(self):
         if self.current_step > 1:
             self.go_to_step(self.current_step - 1)

    def go_to_step(self, step_number):
        if step_number > self.current_step:
             #validate current state before going to next
             if self.current_step == 2 and step_number ==3: #validate extraction parameters.
                 if not self.working_folder_path.text() or not self.iso_file_path.text():
                      QMessageBox.warning(self, "Warning", "Please select working folder and ISO file.")
                      return

             elif self.current_step == 5 and step_number == 6: #validate selection
                  packages_to_remove = self.step5_package_model.get_checked_packages()
                  if not packages_to_remove:
                       QMessageBox.warning(self, "Warning", "No packages selected for removal.")
                       return

        # Hide all steps
        self.step3_group.hide()
        self.step4_group.hide()
        self.step5_group.hide()
        self.step6_group.hide()
        self.step7_boot_group.hide()
        self.step8_group.hide()

        # Show the requested step and update buttons/state
        if step_number == 1:  # Working Folder and ISO selection
            self.layout().itemAt(0).widget().show()  # step1_group
            self.layout().itemAt(1).widget().show()  # iso_info_group
            self.next_button.show()
            self.back_button.hide()

        elif step_number == 2:  # Should not be directly accessible
            self.layout().itemAt(0).widget().show()
            self.layout().itemAt(1).widget().show()
            self.next_button.show()
            self.back_button.hide()


        elif step_number == 3:  # ISO Extraction
            self.step3_group.show()
            self.next_button.show()
            self.back_button.show()
            self.back_button.setEnabled(False) #disable going back during extraction
            self.next_button.setEnabled(False) #disable next until extraction is complete.
            self._extract_iso()  # Start extraction

        elif step_number == 4:  # Chroot Terminal
            self.step4_group.show()
            self.terminal_stop_button.show()
            self.next_button.show()
            self.back_button.show()
            self.step4_terminal.setFocus()
            self.step4_terminal.setPlainText(f"# Type 'help' for basic commands.\n\n$ ")
            self.step4_terminal.moveCursor(QTextCursor.MoveOperation.End)

        elif step_number == 5:  # Package Removal List
            self.step5_group.show()
            self.step5_refresh_button.show()
            self.next_button.show()
            self.back_button.show()
            if not self.step5_package_model._package_data: #don't repopulate on back
               self.refresh_package_list()


        elif step_number == 6:  # Confirm and Execute Package Removal
            self.step6_group.show()
            self.step6_progress_label.show()
            self.step6_progress_bar.show()
            self.next_button.show()  # Show Next button
            self.back_button.show()
            self.step6_confirm_button.show() #show button.
            self.next_button.setEnabled(False) #disable until removal is done.
            self.back_button.setEnabled(False) #disable until removal is done.

            packages_to_remove = self.step5_package_model.get_checked_packages()
            self.step6_package_list_display.clear()
            if packages_to_remove:
                self.step6_package_list_display.setPlainText("Packages to be removed:\n" + "\n".join(packages_to_remove))
                self._execute_package_removal(packages_to_remove)  # Start removal in the background
            else: #should not happen, but handle for robustness.
                self.step6_package_list_display.setPlainText("No packages selected for removal.")
                self.step6_progress_label.hide()  # Hide if no removal
                self.step6_progress_bar.hide()
                self.next_button.setEnabled(True) #reenable next.
                self.back_button.setEnabled(True)

        elif step_number == 7: #recreate ISO
            self.step7_boot_group.show()
            self.step7_progress_bar.hide()  # Initially hide progress bar
            self.step7_log_display.hide()
            self.next_button.show()
            self.back_button.show()


        elif step_number == 8:  # Finish
            self.step8_group.show()
            self.next_button.setText("Finish")  # Change button text
            self.back_button.hide()  # No back button on the final step
            iso_file_name = os.path.basename(self.output_iso_path.text())
            self.step8_summary_label.setText("Custom ISO creation completed successfully!")
            self.step8_output_path_display.setText(f"ISO file saved to: {self.output_iso_path.text()}")


        self.current_step = step_number


    def _extract_iso(self):

        working_folder = self.working_folder_path.text()
        iso_file = self.iso_file_path.text()
        self.extracted_iso_path = os.path.join(working_folder, "extracted_iso")
        os.makedirs(self.extracted_iso_path, exist_ok=True)

        self.step3_progress_bar.setValue(0)
        self.step3_progress_bar.setFormat("%p% - Extracting...")

        try:
            iso_file = self.iso_file_path.text()
             # Use xorriso for extraction
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
        # Parse xorriso output to estimate progress (very basic)
        if "filesினாலும்" in output_text: #basic percentage
            try:
                parts = output_text.split("filesினாலும்")
                numbers = parts[0].split()
                current = int(numbers[-2].strip())
                total = int(numbers[-1].strip())
                percent = int((current / total) * 100)
                self.step3_progress_bar.setValue(percent)

            except (ValueError, IndexError):
                pass  # Ignore parsing errors, just update the text


    def _extraction_finished(self, return_code):
        if return_code == 0:
            self.step3_progress_bar.setValue(100)
            self.step3_progress_bar.setFormat("%p% - Extraction Complete")
            print("ISO extraction completed.")
            self.back_button.setEnabled(True) #reenable now
            self.next_button.setEnabled(True)

        else:
            self.step3_progress_bar.setFormat("Extraction Failed")
            QMessageBox.critical(self, "Error", "ISO extraction failed.")
            print("Error during ISO extraction.")
            self.back_button.setEnabled(True) #extraction failed, still allow going back.

    def browse_boot_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Boot Logo Image", "", "Images (*.png *.jpg *.bmp *.svg *.xpm)")
        if file_path:
            self.boot_logo_path = file_path
            # Display a small preview
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.boot_logo_preview.setPixmap(scaled_pixmap)
            else: #invalid image
                 self.boot_logo_preview.setText("Invalid Image")
            print(f"Boot logo selected: {file_path}")

    def eventFilter(self, obj, event):
        if obj == self.step4_terminal and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                command = self._get_terminal_command()
                if command:
                    self._start_command_execution(command)
                return True  # Consume the event
            elif event.key() == Qt.Key.Key_Up:
                self._navigate_command_history(-1)
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_command_history(1)
                return True
        return super().eventFilter(obj, event)

    def _get_terminal_command(self):
        text_content = self.step4_terminal.toPlainText()
        prompt_index = text_content.rfind("$ ")
        if prompt_index != -1:
            command_start_index = prompt_index + 2
            command = text_content[command_start_index:].strip()
            if command:  # Avoid empty commands
                self.step4_terminal_command_history.append(command)
                self.step4_terminal_history_index = len(self.step4_terminal_command_history) #set to the latest.
                return command
        return None

    def _start_command_execution(self, command):
        if self.command_runner_thread and self.command_runner_thread.isRunning():
            self._append_to_terminal("\nPrevious command still running. Please wait or stop it.\n$ ")
            return

        help_command = command.strip().lower()
        if help_command == "help":
            help_text = (
                "\nAvailable commands:\n"
                "  help - Show this help message\n"
                "  ls   - List files in current directory (in chroot)\n"
                "  pwd  - Print working directory (in chroot)\n"
                "  echo <text> - Print text (in chroot)\n"
                "  exit - Exit chroot environment\n"
                "  apt update - Update package lists (requires sudo)\n"
                "  apt install <package> - Install package (requires sudo)\n"
                "  apt remove <package> - Remove package (requires sudo)\n"
                "  dpkg -i <package.deb> - Install a .deb package (requires sudo)\n"
                "  dpkg -r <package> - Remove a package (requires sudo)\n" #Added dpkg
            )
            self._append_to_terminal(help_text + "\n$ ")
            return
        elif help_command == "exit":
             # Exiting the chroot and advancing.
            self._append_to_terminal("\nExiting chroot environment.\n")
            self.go_to_step(5) #go to next step
            return

        self._append_to_terminal("\n")  # Newline before output
        self.terminal_stop_button.show()

        # Run commands with chroot
        self.command_runner_thread = CommandRunnerThread([command], chroot_path=self.extracted_iso_path)
        self.command_runner_thread.command_output_signal.connect(self._append_to_terminal)
        self.command_runner_thread.command_finished_signal.connect(self._command_execution_finished)
        self.command_runner_thread.start()

    def _command_execution_finished(self, return_code):
        self.terminal_stop_button.hide()
        self._append_to_terminal("$ ")  # Ready for next command
        self.command_runner_thread = None
        # You might want to handle non-zero return codes here (errors)

    def stop_terminal_command(self):
        if self.command_runner_thread and self.command_runner_thread.isRunning():
            self.command_runner_thread.stop_thread()
            self._append_to_terminal("\n[Command stopped by user]\n$ ")
            self.command_runner_thread = None #cleanup

    def _append_to_terminal(self, text):
        self.step4_terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.step4_terminal.insertPlainText(text)
        self.step4_terminal.moveCursor(QTextCursor.MoveOperation.End) #ensure always at end.

    def _navigate_command_history(self, direction):
        if not self.step4_terminal_command_history:
            return

        self.step4_terminal_history_index += direction
        # Wrap around
        if self.step4_terminal_history_index < 0:
            self.step4_terminal_history_index = len(self.step4_terminal_command_history) -1
        elif self.step4_terminal_history_index >= len(self.step4_terminal_command_history):
             self.step4_terminal_history_index = 0 # Loop back to the beginning

        if self.step4_terminal_command_history: #check again in case it was empty
              command_to_set = self.step4_terminal_command_history[self.step4_terminal_history_index]
              text_content = self.step4_terminal.toPlainText()
              prompt_index = text_content.rfind("$ ")
              if prompt_index != -1:
                text_before_prompt = text_content[:prompt_index+2] # Keep existing text
                self.step4_terminal.setPlainText(text_before_prompt + command_to_set)
                self.step4_terminal.moveCursor(QTextCursor.MoveOperation.End)

    def refresh_package_list(self):
        self.step5_refresh_button.setEnabled(False) #prevent multiple clicks.
        self._populate_package_list() #call the actual population.

    def _populate_package_list(self):

        self.step5_package_model.clear_package_statuses()
        self.step5_package_model._package_data = []  # Clear existing data
        self.step5_package_model.layoutAboutToBeChanged.emit()


        command = ["apt", "list", "--installed"]
        self._append_to_terminal(f"\nFetching installed package list...\n")


        self.package_list_thread = CommandRunnerThread(command, chroot_path = self.extracted_iso_path)
        self.package_list_thread.command_output_signal.connect(self._process_package_list_output)
        self.package_list_thread.command_finished_signal.connect(self._package_list_fetch_finished)
        self.package_list_thread.start()


    def _process_package_list_output(self, output_text):
        lines = output_text.strip().split('\n')
        package_data = []
        for line in lines:
            if "/" in line and ",now" in line:  # Check for valid package lines
                parts = line.split()
                package_name_parts = parts[0].split("/")
                package_name = package_name_parts[0]
                version_part = parts[1].split(",")
                version = version_part[0]
                # Add to data with 'remove' flag initially set to False
                package_data.append({'name': package_name, 'version': version, 'remove': False})
        if package_data:
            # Append to existing data
            current_data = self.step5_package_model._package_data
            updated_data = current_data + package_data
            self.step5_package_model._package_data = updated_data
            self.step5_package_model.layoutChanged.emit() #refresh UI
            self.step5_proxy_model.invalidateFilter()  # Apply filter

    def _package_list_fetch_finished(self, return_code):
        self._append_to_terminal(f"\nPackage list fetched.\n")
        self.step5_refresh_button.setEnabled(True)
        self.package_list_thread = None #cleanup.

    def _filter_package_list(self, filter_text):
        self.step5_proxy_model.setFilterText(filter_text)

    def confirm_package_removal(self):
          # Confirmation is now handled in go_to_step(6)
          self.go_to_step(6)

    def _execute_package_removal(self, packages_to_remove):
        if not packages_to_remove:
            self._package_removal_finished(0)  # Treat empty list as success
            return

        # Mark packages as "removing"
        for pkg in packages_to_remove:
            self.step5_package_model.set_package_status(pkg, 'removing')

        # Remove packages one by one to handle dependencies gracefully
        self.packages_to_remove_queue = packages_to_remove.copy()  # Create a copy
        self.current_package_index = 0
        self.total_packages_to_remove = len(self.packages_to_remove_queue)
        self.step6_progress_bar.setValue(0) #reset
        self._remove_next_package()


    def _remove_next_package(self):
        if self.current_package_index >= len(self.packages_to_remove_queue):
            #all packages removed.
            self._package_removal_finished(0)
            return

        package = self.packages_to_remove_queue[self.current_package_index]
        remove_command = ["apt-get", "purge", "-y", package] #single package at a time.

        self.package_removal_thread = CommandRunnerThread(remove_command, chroot_path = self.extracted_iso_path)
        self.package_removal_thread.command_output_signal.connect(self._process_package_removal_output)
        self.package_removal_thread.command_finished_signal.connect(self._handle_single_package_removal)
        self.package_removal_thread.start()

    def _handle_single_package_removal(self, return_code):
          package_removed = self.packages_to_remove_queue[self.current_package_index]

          if return_code == 0:
            self.step5_package_model.set_package_status(package_removed, 'removed') #success
          else:
              self.step5_package_model.set_package_status(package_removed, 'error') #failure.
              QMessageBox.critical(self,"Package Removal Error", f"Failed to remove {package_removed}")


          self.current_package_index +=1
          progress_percentage = int((self.current_package_index / self.total_packages_to_remove) * 100)
          self.step6_progress_bar.setValue(progress_percentage)

          #proceed to the next package.
          self._remove_next_package()


    def _process_package_removal_output(self, output_text):
        self.step6_package_list_display.moveCursor(QTextCursor.MoveOperation.End)
        self.step6_package_list_display.insertPlainText(output_text)
        self.step6_package_list_display.moveCursor(QTextCursor.MoveOperation.End)


    def _package_removal_finished(self, return_code):
        self.package_removal_thread = None
        self.step6_confirm_button.hide() #Hide confirm button.
        self.step6_progress_label.hide() #Hide progress label
        self._append_to_terminal("\nPackage removal process finished.\n")
        self.step6_package_list_display.insertPlainText("\nPackage removal process finished.\n")
        self.next_button.setEnabled(True) #reenable next
        self.back_button.setEnabled(True) #reenable back


    def _start_iso_recreation(self):
        output_iso_file = self.output_iso_path.text()

        if not output_iso_file:
            QMessageBox.warning(self, "Warning", "Please specify output ISO path.")
            return
        if not self.compression_options: #default
             self.compression_options = {"method": "gzip", "level": 6, "threads": 0, "custom_command":""}

        self.step7_log_display.clear()
        self.step7_progress_bar.setValue(0)
        self.step7_progress_bar.show()
        self.step7_log_display.show()
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)
        # Prepare xorriso command
        cmd = [
            "xorriso",
            "-as", "mkisofs",
            "-r",  # Rational Rock (Rock Ridge)
            "-J",  # Joliet
            "-joliet-long", #long filenames
            "-l", #allow full 31 character filenames for Rock Ridge.
            "-cache-inodes",
            "-follow-links",
            "-o", output_iso_file,
            "-b", "isolinux/isolinux.bin",  # Boot image (adjust path if needed)
            "-c", "isolinux/boot.cat",      # Boot catalog (adjust path)
            "-no-emul-boot",
            "-boot-load-size", "4",
            "-boot-info-table",
            "-isohybrid-mbr", "isolinux/isohdpfx.bin", #isohybrid for BIOS.
            "-eltorito-alt-boot", #for EFI booting
            "-e", "boot/grub/efi.img", #use efi image.
            "-no-emul-boot", #required after -e
            "-isohybrid-gpt-basdat", #mark data partition as bootable in GPT
        ]

        # Add preseed file if specified
        if self.preseed_file and os.path.exists(self.preseed_file):
             cmd.extend(["-preseed", self.preseed_file])

        # Add boot logo if specified
        if self.boot_logo_path and os.path.exists(self.boot_logo_path):
            # Copy the boot logo into the extracted ISO
            isolinux_dir = os.path.join(self.extracted_iso_path, "isolinux")
            if not os.path.exists(isolinux_dir):
                os.makedirs(isolinux_dir)

            logo_dest_path = os.path.join(isolinux_dir, "logo.png")  # Use a consistent name
            try:
                shutil.copy(self.boot_logo_path, logo_dest_path)

                # Modify isolinux.cfg (or syslinux.cfg) to use the logo
                cfg_path = os.path.join(isolinux_dir, "isolinux.cfg")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "a") as cfg_file:
                         cfg_file.write(f"\nUI vesamenu.c32\nMENU BACKGROUND logo.png\n") #modify config
            except (shutil.Error, IOError) as e:
                 QMessageBox.warning(self, "Warning", f"Failed to copy boot logo: {e}")

        # Add the source directory (extracted ISO content)
        cmd.append(self.extracted_iso_path)

        self.iso_recreation_thread = CommandRunnerThread(cmd, working_dir = self.working_folder_path.text()) #command, and the working directory
        self.iso_recreation_thread.command_output_signal.connect(self._process_iso_recreation_output)
        self.iso_recreation_thread.command_finished_signal.connect(self._iso_recreation_finished)
        self.iso_recreation_thread.start()

    def _process_iso_recreation_output(self, output_text):
        self.step7_log_display.moveCursor(QTextCursor.MoveOperation.End)
        self.step7_log_display.insertPlainText(output_text)
        self.step7_log_display.moveCursor(QTextCursor.MoveOperation.End)

        # Attempt to extract progress percentage from xorriso output
        if "xorriso : UPDATE : " in output_text:
            try:
                parts = output_text.split(":")
                progress_part = parts[-1].strip() #get last element
                if progress_part.endswith("%"):
                   progress_percent = int(progress_part[:-1]) #remove %
                   self.step7_progress_bar.setValue(progress_percent)
            except (ValueError, IndexError):
                pass

    def _iso_recreation_finished(self, return_code):
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(True)
        if return_code == 0:
             self.step7_progress_bar.setValue(100)
        else:
           self.step7_progress_bar.setFormat("ISO Creation Failed") #indicate error.
           QMessageBox.critical(self, "Error", f"ISO re-creation failed with return code {return_code}.") #show return code

        self.iso_recreation_thread = None
        self.go_to_step(8) #go to the final step regardless.

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # A more modern style
    iso_builder_app = ISOMasterBuilderApp()
    iso_builder_app.show()
    sys.exit(app.exec())