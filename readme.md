# ISO Master Builder

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

This project builds and customizes ISO images.
The code is organized into several modules:

- **widgets.py**: Contains custom Qt widgets (e.g., `ElidedLabel` and `CenteredIconDelegate`).
- **threads.py**: Contains `CommandRunnerThread` for running shell commands without blocking the UI.
- **package_models.py**: Implements package list models and a filter proxy for managing packages.
- **dialogs.py**: Provides dialogs for preseed options, kernel selection, and advanced compression settings.
- **MasterLinux.py**: The main file that initializes the GUI and integrates all modules.

## Features

*   **Intuitive GUI:**  A step-by-step interface guides you through the entire process.
*   **Chroot Environment:**  An integrated terminal provides a chroot environment for full control over the ISO's contents.  You can use familiar `apt` commands (and other shell commands) to customize the system.
*   **Package Management:** Easily view and select installed packages for removal.  A filterable list helps you find what you need.  Package removal is handled *one at a time* to ensure proper dependency resolution.
*   **Progress Updates:** Real-time progress bars and output logs keep you informed during lengthy operations (extraction, package removal, ISO creation).
*   **Error Handling:**  Robust error handling and informative messages guide you if anything goes wrong.
*   **Command History:**  The chroot terminal supports command history (up/down arrow keys).
*   **ISO Information Extraction:**  Automatically extracts basic ISO information (name, version) using `xorriso`.
*   **Boot Logo Customization:**  Option to include a custom boot logo in your ISO.
*   **Preseed File Support:**  Automate the installation process by providing a preseed file.
* **Kernel Selection:** Ability to change the kernel installed inside of the ISO.
* **Advanced Compression Options:** The tool allows for choosing the compression method for the resulting `.iso` with levels, threads, and custom commands.
* **Temporary File Management:** Includes a checkbox to automatically delete the temporary extraction directory after ISO creation.

## Requirements

*   **Python 3.12+:** The application is written in Python and requires a compatible interpreter.
*   **xorriso:**  Used for ISO extraction and creation.  Make sure it's installed and in your system's `PATH`.
*   **Administrator Privileges:**  `sudo` access is required for operations within the chroot environment (e.g., `apt install`, `apt remove`).

## Installation

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/john0n1/linuxmkr.git 
    cd linuxmkr
    ```

2.  **Install Dependencies:**

    ```bash
    # Create a virtual-env
    python3 -m venv venv
    # Activate the virtual-Env 
    Source venv/bin/activate
    pip install -r requirements.txt

    # Install xorriso (example for Debian/Ubuntu)
    sudo apt update
    sudo apt install xorriso
    ```

3. **Project Structure**

   The project is structured as follows to enhance maintainability and readability:
    - **`MasterLinux.py`**: The main file that initializes the GUI and integrates all modules.
    - **`widgets.py`**: Contains custom Qt widgets (e.g., `ElidedLabel` and `CenteredIconDelegate`).
    - **`threads.py`**: Contains `CommandRunnerThread` for running shell commands without blocking the UI.
    - **`package_models.py`**: Implements package list models and a filter proxy for managing packages.
    - **`dialogs.py`**: Provides dialogs for preseed options, kernel selection, and advanced compression settings.
    - **`README.md`**: Documentation.

4. To ensure that the application works as a whole make sure all of the python files are inside the same directory.

## Usage

1.  **Run the Application:**

    ```bash
    python MasterLinux.py
    ```

2.  **Follow the On-Screen Instructions:**

    *   **Step 1: Working Folder:** Select a directory where temporary files will be stored.  This folder should have enough free space (at least the size of the ISO you're working with).
    *   **Step 2: ISO File:** Choose the base ISO image you want to customize. The application will attempt to extract the ISO's name, version, and architecture. Optionally select a boot logo.
    *   **Step 3: ISO Extraction:** The application extracts the ISO to the working folder.  A progress bar shows the extraction progress.
    *   **Step 4: Customize ISO (Chroot Terminal):**  Use the integrated terminal to modify the ISO's contents.  You're in a chroot environment, so you can use commands like `apt update`, `apt install <package>`, `apt remove <package>`, `ls`, `pwd`, etc. Type `help` in the terminal for a list of basic commands. Use `exit` in the terminal to finish customization and proceed to the next step.
    *   **Step 5: Package Removal:**  A list of installed packages is displayed.  Use the checkboxes to select packages you want to remove. You can search/filter the list.
    *   **Step 6: Confirm Package Removal:**  Review the list of packages to be removed.  The removal process is executed *one package at a time* to handle dependencies correctly.
    *   **Step 7: Re-create ISO:**  Specify the output path and filename for the customized ISO.  You can set advanced compression options. A preseed file is optional.
    *   **Step 8: Finished:** The new ISO is created. You can choose to open the output folder and/or delete the temporary files.

## File Structure

```
/home/mitanderos/MasterLinux/
  ├── MasterLinux.py
  ├── widgets.py
  ├── threads.py
  ├── package_models.py
  ├── dialogs.py
  └── readme.md
```

## Troubleshooting

*   **`xorriso` not found:**  Ensure that `xorriso` is installed and in your system's `PATH`.
*   **GUI Freezing:**  Long operations (especially `apt` commands) can take time.  The application uses threads to prevent the GUI from completely freezing, but some operations are inherently slow.
*   **Package Removal Errors:** If a package fails to remove, check the terminal output for error messages. It may be due to dependency conflicts.  Try removing packages individually to isolate the problem.
*   **Permission Denied:** Make sure you have the necessary permissions to access the working folder, ISO file, and to execute commands within the chroot environment (using `sudo`).

## Contributing

Contributions are welcome!  Please follow these guidelines:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them with clear, descriptive messages.
4.  Create a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool modifies system images.  Use it with caution and at your own risk.  It's recommended to test your customized ISOs in a virtual machine before deploying them to physical hardware. The author is not responsible for any damage caused by the use of this software.