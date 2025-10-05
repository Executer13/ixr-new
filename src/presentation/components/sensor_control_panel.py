"""
Sensor Control Panel - Reusable component for sensor connection controls.

This component provides a clean, modern interface for controlling a single sensor,
including connection/disconnection buttons and status indicators.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from gui.modern_theme import ModernTheme


class SensorControlPanel(QWidget):
    """
    Control panel for a single sensor.

    Provides:
    - Connect/Disconnect buttons
    - Connection status indicator
    - Streaming status indicator
    - Status text display

    Signals:
        connect_requested: Emitted when connect button is clicked
        disconnect_requested: Emitted when disconnect button is clicked
    """

    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()

    def __init__(self, sensor_name: str, parent=None):
        """
        Initialize the sensor control panel.

        Args:
            sensor_name: Display name for the sensor (e.g., "Muse", "Polar H10")
            parent: Parent widget
        """
        super().__init__(parent)
        self._sensor_name = sensor_name
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.connect_button = QPushButton(f"Connect {self._sensor_name}")
        self.connect_button.setStyleSheet(ModernTheme.get_button_style('primary'))
        self.connect_button.clicked.connect(self.connect_requested.emit)
        button_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton(f"Disconnect {self._sensor_name}")
        self.disconnect_button.setStyleSheet(ModernTheme.get_button_style('danger'))
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.disconnect_button)

        layout.addLayout(button_layout)

        # Status indicators layout
        self.connection_circle = QLabel()
        self.connection_text = QLabel("Disconnected")
        self.stream_circle = QLabel()
        self.stream_text = QLabel("Not Streaming")

        self._set_indicator(self.connection_circle, self.connection_text, "Disconnected", "red")
        self._set_indicator(self.stream_circle, self.stream_text, "Not Streaming", "red")

        status_layout = QGridLayout()
        status_layout.setSpacing(12)
        status_layout.setContentsMargins(16, 16, 16, 16)

        conn_label = QLabel(f"{self._sensor_name} Connection:")
        conn_label.setStyleSheet(ModernTheme.get_label_style('secondary'))
        stream_label = QLabel(f"{self._sensor_name} Stream:")
        stream_label.setStyleSheet(ModernTheme.get_label_style('secondary'))

        status_layout.addWidget(conn_label, 0, 0, Qt.AlignRight)
        status_layout.addWidget(self.connection_circle, 0, 1, Qt.AlignRight)
        status_layout.addWidget(self.connection_text, 0, 2)

        status_layout.addWidget(stream_label, 1, 0, Qt.AlignRight)
        status_layout.addWidget(self.stream_circle, 1, 1, Qt.AlignRight)
        status_layout.addWidget(self.stream_text, 1, 2)

        layout.addLayout(status_layout)

    def _set_indicator(self, label_circle: QLabel, label_text: QLabel,
                       status_text: str, color: str):
        """
        Update indicator with modern styling.

        Args:
            label_circle: Circle indicator label
            label_text: Text status label
            status_text: Status text to display
            color: Color for the indicator (e.g., "red", "green", "yellow")
        """
        label_text.setText(status_text)
        label_text.setStyleSheet(ModernTheme.get_label_style('primary'))

        # Create glow effect
        label_circle.setGraphicsEffect(ModernTheme.create_glow_effect(color, blur_radius=16))

        label_circle.setStyleSheet(
            f"""
            border-radius: 7px;
            min-width: 14px;
            min-height: 14px;
            max-width: 14px;
            max-height: 14px;
            background-color: {color};
            margin-right: 10px;
            """
        )

    def update_status(self, status: str):
        """
        Update sensor status based on status message.

        Args:
            status: Status message from the sensor
        """
        status_lower = status.lower()

        # Update connection status
        if any(x in status_lower for x in ["connected", "alive"]):
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self._set_indicator(self.connection_circle, self.connection_text,
                              "Connected", "green")
        elif any(x in status_lower for x in ["disconnected", "connection failed", "error"]):
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self._set_indicator(self.connection_circle, self.connection_text,
                              "Disconnected", "red")

        # Update streaming status
        if any(x in status_lower for x in ["streaming", "lsl stream started", "lsl stream resumed", "ecg data is now arriving"]):
            self._set_indicator(self.stream_circle, self.stream_text,
                              "Streaming", "green")
        elif any(x in status_lower for x in ["not streaming", "lsl stream paused", "stream stopped"]):
            self._set_indicator(self.stream_circle, self.stream_text,
                              "Not Streaming", "red")
        elif "lsl stream created" in status_lower:
            self._set_indicator(self.stream_circle, self.stream_text,
                              "Ready", "yellow")

    def set_enabled(self, enabled: bool):
        """
        Enable or disable all controls.

        Args:
            enabled: Whether to enable controls
        """
        self.connect_button.setEnabled(enabled)
        self.disconnect_button.setEnabled(enabled)

    def reset(self):
        """Reset the panel to default state."""
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_indicator(self.connection_circle, self.connection_text,
                          "Disconnected", "red")
        self._set_indicator(self.stream_circle, self.stream_text,
                          "Not Streaming", "red")
