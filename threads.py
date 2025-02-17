import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

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
                # ...existing code for chroot handling...
                final_command = self.command  # placeholder
            else:
                # ...existing code...
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
                # ...existing code to read output...
                break  # placeholder loop exit

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
