"""
Log Viewer - Reusable component for displaying application logs.

This component provides a clean, modern interface for viewing log messages
with optional filtering and clearing capabilities.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import pyqtSignal
from gui.modern_theme import ModernTheme


class LogViewer(QWidget):
    """
    Log viewer component with modern styling.

    Provides:
    - Read-only text area for logs
    - Optional clear button
    - Auto-scrolling to latest log
    - Modern themed styling

    Signals:
        clear_requested: Emitted when clear button is clicked
    """

    clear_requested = pyqtSignal()

    def __init__(self, title: str = "Log / Status", show_clear_button: bool = True, parent=None):
        """
        Initialize the log viewer.

        Args:
            title: Title text for the log viewer
            show_clear_button: Whether to show the clear button
            parent: Parent widget
        """
        super().__init__(parent)
        self._title = title
        self._show_clear_button = show_clear_button
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header with title and optional clear button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_label = QLabel(self._title)
        title_label.setStyleSheet(ModernTheme.get_label_style('title'))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if self._show_clear_button:
            self.clear_button = QPushButton("Clear")
            self.clear_button.setStyleSheet(ModernTheme.get_button_style('secondary'))
            self.clear_button.clicked.connect(self._on_clear_clicked)
            header_layout.addWidget(self.clear_button)

        layout.addLayout(header_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(ModernTheme.get_textedit_style())
        self.log_text.setMinimumHeight(150)
        layout.addWidget(self.log_text)

    def append_log(self, message: str):
        """
        Append a log message to the viewer.

        Args:
            message: Log message to append
        """
        self.log_text.append(message)
        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def append_html(self, html: str):
        """
        Append HTML-formatted content to the viewer.

        Args:
            html: HTML content to append
        """
        self.log_text.append(html)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def clear(self):
        """Clear all log messages."""
        self.log_text.clear()

    def set_text(self, text: str):
        """
        Set the entire log text content.

        Args:
            text: Text content to set
        """
        self.log_text.setPlainText(text)

    def get_text(self) -> str:
        """
        Get all log text content.

        Returns:
            str: Current log text content
        """
        return self.log_text.toPlainText()

    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.clear()
        self.clear_requested.emit()

    def set_max_block_count(self, max_blocks: int):
        """
        Set maximum number of text blocks to keep.

        This helps prevent memory issues with very long logs.

        Args:
            max_blocks: Maximum number of blocks (lines) to keep
        """
        self.log_text.document().setMaximumBlockCount(max_blocks)
