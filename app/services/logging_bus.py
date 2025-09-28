"""
This module defines a simple event bus for logging, allowing different parts
of the application to emit log messages that can be displayed in the UI.
"""

# =============================
# services/logging_bus.py
# =============================
from PyQt5.QtCore import QObject, pyqtSignal


class LogBus(QObject):
    """
    A simple event bus for logging.

    It uses a PyQt signal to allow components in different threads to safely
    send log messages to the main UI thread.
    """

    sig_log = pyqtSignal(str)

    def log(self, msg: str):
        """
        Emits a log message.

        Args:
            msg (str): The message to log.
        """
        self.sig_log.emit(msg)
