# dashboard.py

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QTabWidget,
    QLabel, QGridLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QColor
from src.infrastructure.sensors.muse_sensor import MuseSensor
from src.infrastructure.sensors.polar_sensor import PolarSensor
from gui.lsl_browser_widget import LSLBrowserWidget
from gui.plot_tab import PlotTab
from src.infrastructure.streaming.lsl_fetcher import LSLFetcher
from src.presentation.components.brain_power_analysis_module import BrainPowerAnalysisModule
from gui.modern_theme import ModernTheme

def set_indicator(label_circle: QLabel, label_text: QLabel, status_text: str, color: str):
    """
    Update two parts of an indicator with modern Apple-inspired styling:
      1) label_circle: a modern circular indicator with glow effect
      2) label_text: textual status with modern typography
    """
    label_text.setText(status_text)
    label_text.setStyleSheet(ModernTheme.get_label_style('primary'))

    # Create glow effect for the indicator using ModernTheme (reduced intensity)
    label_circle.setGraphicsEffect(ModernTheme.create_glow_effect(color, blur_radius=8))

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

class Dashboard(QWidget):
    def __init__(self, parent=None):
        super(Dashboard, self).__init__(parent)
        self.muse_sensor = MuseSensor()
        self.polar_sensor = PolarSensor()
        self.lsl_fetcher = LSLFetcher()

        # OPTIMIZATION: Debounce timer for tab changes (reduce lag)
        self.tab_change_timer = QTimer()
        self.tab_change_timer.setSingleShot(True)
        self.tab_change_timer.setInterval(100)  # 100ms debounce
        self.tab_change_timer.timeout.connect(self._handle_tab_changed_delayed)
        self.pending_tab_index = None

        # Stream cache to avoid repeated LSL discovery
        self.stream_cache = []
        self.stream_cache_time = 0

        self.init_ui()

        self.muse_sensor.status_changed.connect(self.handle_muse_status_update)
        self.polar_sensor.status_changed.connect(self.handle_polar_status_update)
        self.tabs.currentChanged.connect(self.handle_tab_changed)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Modern tab widget with Apple-inspired styling
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(ModernTheme.get_tab_widget_style())
        main_layout.addWidget(self.tabs)

        # =========== Sensors Tab ============
        sensors_tab = QWidget()
        sensors_tab.setStyleSheet(ModernTheme.get_widget_style())
        sensors_layout = QVBoxLayout(sensors_tab)
        sensors_layout.setContentsMargins(16, 16, 16, 16)
        sensors_layout.setSpacing(12)

        # ===== MUSE CARD =====
        muse_card = QWidget()
        muse_card.setStyleSheet(ModernTheme.get_card_style())
        muse_card_layout = QVBoxLayout(muse_card)
        muse_card_layout.setContentsMargins(12, 12, 12, 12)
        muse_card_layout.setSpacing(10)

        # MUSE Title
        muse_title = QLabel("Muse Sensor")
        muse_title.setStyleSheet(ModernTheme.get_label_style('title'))
        muse_card_layout.addWidget(muse_title)

        # MUSE Control Buttons
        muse_button_layout = QHBoxLayout()
        muse_button_layout.setSpacing(12)

        self.muse_connect_button = QPushButton("Connect Muse")
        self.muse_disconnect_button = QPushButton("Disconnect Muse")

        # Apply modern theme button styles
        self.muse_connect_button.setStyleSheet(ModernTheme.get_button_style('primary'))
        self.muse_disconnect_button.setStyleSheet(ModernTheme.get_button_style('danger'))

        muse_button_layout.addWidget(self.muse_connect_button)
        muse_button_layout.addWidget(self.muse_disconnect_button)
        muse_card_layout.addLayout(muse_button_layout)

        # MUSE Indicators (2 rows: Connection, Streaming)
        self.muse_connection_circle = QLabel()
        self.muse_connection_text   = QLabel("Disconnected")
        self.muse_stream_circle     = QLabel()
        self.muse_stream_text       = QLabel("Not Streaming")
        set_indicator(self.muse_connection_circle, self.muse_connection_text, "Disconnected", "red")
        set_indicator(self.muse_stream_circle,     self.muse_stream_text,     "Not Streaming", "red")

        muse_status_layout = QGridLayout()
        muse_status_layout.setSpacing(12)
        muse_status_layout.setContentsMargins(0, 12, 0, 0)

        # Apply modern label styling
        muse_conn_label = QLabel("Muse Connection:")
        muse_conn_label.setStyleSheet(ModernTheme.get_label_style('secondary'))
        muse_stream_label = QLabel("Muse Stream:")
        muse_stream_label.setStyleSheet(ModernTheme.get_label_style('secondary'))

        muse_status_layout.addWidget(muse_conn_label, 0, 0, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_connection_circle, 0, 1, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_connection_text,   0, 2)

        muse_status_layout.addWidget(muse_stream_label,      1, 0, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_stream_circle,     1, 1, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_stream_text,       1, 2)

        muse_card_layout.addLayout(muse_status_layout)
        sensors_layout.addWidget(muse_card)

        # ===== POLAR CARD =====
        polar_card = QWidget()
        polar_card.setStyleSheet(ModernTheme.get_card_style())
        polar_card_layout = QVBoxLayout(polar_card)
        polar_card_layout.setContentsMargins(12, 12, 12, 12)
        polar_card_layout.setSpacing(10)

        # POLAR Title
        polar_title = QLabel("Polar H10 Sensor")
        polar_title.setStyleSheet(ModernTheme.get_label_style('title'))
        polar_card_layout.addWidget(polar_title)

        # POLAR Control Buttons
        polar_button_layout = QHBoxLayout()
        polar_button_layout.setSpacing(12)

        self.polar_connect_button = QPushButton("Connect Polar H10")
        self.polar_disconnect_button = QPushButton("Disconnect Polar H10")

        # Apply modern theme button styles
        self.polar_connect_button.setStyleSheet(ModernTheme.get_button_style('primary'))
        self.polar_disconnect_button.setStyleSheet(ModernTheme.get_button_style('danger'))

        polar_button_layout.addWidget(self.polar_connect_button)
        polar_button_layout.addWidget(self.polar_disconnect_button)
        polar_card_layout.addLayout(polar_button_layout)

        # POLAR Indicators
        self.polar_connection_circle = QLabel()
        self.polar_connection_text   = QLabel("Disconnected")
        self.polar_stream_circle     = QLabel()
        self.polar_stream_text       = QLabel("Not Streaming")
        set_indicator(self.polar_connection_circle, self.polar_connection_text, "Disconnected", "red")
        set_indicator(self.polar_stream_circle,     self.polar_stream_text,     "Not Streaming", "red")

        polar_status_layout = QGridLayout()
        polar_status_layout.setSpacing(12)
        polar_status_layout.setContentsMargins(0, 12, 0, 0)

        polar_conn_label = QLabel("Polar Connection:")
        polar_conn_label.setStyleSheet(ModernTheme.get_label_style('secondary'))
        polar_stream_label = QLabel("Polar Stream:")
        polar_stream_label.setStyleSheet(ModernTheme.get_label_style('secondary'))

        polar_status_layout.addWidget(polar_conn_label, 0, 0, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_connection_circle, 0, 1, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_connection_text,   0, 2)

        polar_status_layout.addWidget(polar_stream_label,      1, 0, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_stream_circle,     1, 1, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_stream_text,       1, 2)

        polar_card_layout.addLayout(polar_status_layout)
        sensors_layout.addWidget(polar_card)

        # ===== LSL BROWSER CARD =====
        lsl_card = QWidget()
        lsl_card.setStyleSheet(ModernTheme.get_card_style())
        lsl_card_layout = QVBoxLayout(lsl_card)
        lsl_card_layout.setContentsMargins(12, 12, 12, 12)
        lsl_card_layout.setSpacing(10)

        lsl_title = QLabel("Available LSL Streams")
        lsl_title.setStyleSheet(ModernTheme.get_label_style('title'))
        lsl_card_layout.addWidget(lsl_title)

        self.lsl_browser = LSLBrowserWidget(self.lsl_fetcher)
        self.lsl_browser.add_stream_requested.connect(self.on_add_stream)
        self.lsl_browser.remove_stream_requested.connect(self.on_remove_stream)
        lsl_card_layout.addWidget(self.lsl_browser)
        sensors_layout.addWidget(lsl_card)

        # ===== STATUS LOG CARD =====
        log_card = QWidget()
        log_card.setStyleSheet(ModernTheme.get_card_style())
        log_card_layout = QVBoxLayout(log_card)
        log_card_layout.setContentsMargins(12, 12, 12, 12)
        log_card_layout.setSpacing(10)

        status_title = QLabel("Log / Status")
        status_title.setStyleSheet(ModernTheme.get_label_style('title'))
        log_card_layout.addWidget(status_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(ModernTheme.get_textedit_style())
        log_card_layout.addWidget(self.log_text)
        sensors_layout.addWidget(log_card)

        self.tabs.addTab(sensors_tab, "Sensors")

        # =========== Plot Tab ============
        self.plot_tab = PlotTab()
        self.tabs.addTab(self.plot_tab, "Plot")
        self.plot_tab.all_streams_removed.connect(self.lsl_browser.clear_all_plot_markers)
        self.plot_tab.all_streams_removed.connect(self.log_all_streams_removed)
        self.plot_tab.all_streams_removed.connect(self.handle_all_streams_removed)
        self.plot_tab.discover_streams_requested.connect(self.on_discover_streams_from_plot)

        # =========== Analysis Tab ============
        # Pass the muse_sensor so the analysis module can access the board_shim
        self.analysis_widget = BrainPowerAnalysisModule(sensor=self.muse_sensor)
        self.tabs.addTab(self.analysis_widget, "Analysis")

        # =========== Finalize ============
        self.setLayout(main_layout)

        # Wire up Muse
        self.muse_connect_button.clicked.connect(self.connect_muse)
        self.muse_disconnect_button.clicked.connect(self.disconnect_muse)
        self.muse_connect_button.setEnabled(True)
        self.muse_disconnect_button.setEnabled(False)

        # Wire up Polar
        self.polar_connect_button.clicked.connect(self.connect_polar)
        self.polar_disconnect_button.clicked.connect(self.disconnect_polar)
        self.polar_connect_button.setEnabled(True)
        self.polar_disconnect_button.setEnabled(False)

    # -----------------------------------------------------------
    # MUSE
    # -----------------------------------------------------------
    def connect_muse(self):
        self.log("Attempting to connect Muse sensor...")
        self.muse_connect_button.setEnabled(False)
        self.muse_disconnect_button.setEnabled(False)
        self.muse_sensor.connect()

    def disconnect_muse(self):
        self.log("Attempting to disconnect Muse sensor...")
        self.muse_connect_button.setEnabled(False)
        self.muse_disconnect_button.setEnabled(False)
        self.muse_sensor.disconnect()

    def handle_muse_status_update(self, status):
        self.log("Muse sensor status: " + status)

        if status in ["Connected", "Alive", "LSL stream started", "LSL stream resumed"]:
            self.muse_connect_button.setEnabled(False)
            self.muse_disconnect_button.setEnabled(True)
            set_indicator(self.muse_connection_circle, self.muse_connection_text, "Connected", "green")
            set_indicator(self.muse_stream_circle,     self.muse_stream_text,     "Streaming", "green")
            self.lsl_browser.refresh_streams()

        elif status.startswith("Connection failed") or status == "Disconnected" or status.startswith("Error"):
            self.muse_connect_button.setEnabled(True)
            self.muse_disconnect_button.setEnabled(False)
            set_indicator(self.muse_connection_circle, self.muse_connection_text, "Disconnected", "red")
            set_indicator(self.muse_stream_circle,     self.muse_stream_text,     "Not Streaming", "red")
            self.lsl_browser.refresh_streams()

        elif status == "LSL stream paused":
            set_indicator(self.muse_connection_circle, self.muse_connection_text, "Connected", "green")
            set_indicator(self.muse_stream_circle,     self.muse_stream_text,     "Not Streaming", "red")
            self.lsl_browser.refresh_streams()

    # -----------------------------------------------------------
    # POLAR
    # -----------------------------------------------------------
    def connect_polar(self):
        self.log("Attempting to connect Polar H10...")
        self.polar_connect_button.setEnabled(False)
        self.polar_disconnect_button.setEnabled(False)
        self.polar_sensor.connect()

    def disconnect_polar(self):
        self.log("Attempting to disconnect Polar H10...")
        self.polar_connect_button.setEnabled(False)
        self.polar_disconnect_button.setEnabled(False)
        self.polar_sensor.disconnect()

    def handle_polar_status_update(self, status):
        self.log("Polar sensor status: " + status)

        if status in ["Connected", "Alive", "LSL stream created. Data may take a few seconds to appear..."]:
            self.polar_connect_button.setEnabled(False)
            self.polar_disconnect_button.setEnabled(True)
            set_indicator(self.polar_connection_circle, self.polar_connection_text, "Connected", "green")
            set_indicator(self.polar_stream_circle,     self.polar_stream_text,     "Not Streaming", "red")
            self.lsl_browser.refresh_streams()

        elif "ECG data is now arriving!" in status:
            self.polar_connect_button.setEnabled(False)
            self.polar_disconnect_button.setEnabled(True)
            set_indicator(self.polar_connection_circle, self.polar_connection_text, "Connected", "green")
            set_indicator(self.polar_stream_circle,     self.polar_stream_text,     "Streaming", "green")
            self.lsl_browser.refresh_streams()

        elif status.startswith("Connection failed") or status == "Disconnected" or status.startswith("Error"):
            self.polar_connect_button.setEnabled(True)
            self.polar_disconnect_button.setEnabled(False)
            set_indicator(self.polar_connection_circle, self.polar_connection_text, "Disconnected", "red")
            set_indicator(self.polar_stream_circle,     self.polar_stream_text,     "Not Streaming", "red")
            self.lsl_browser.refresh_streams()

    # -----------------------------------------------------------
    # LSL Browser integration
    # -----------------------------------------------------------
    def on_add_stream(self, stream_info):
        print(f"[DASHBOARD DEBUG] on_add_stream called for: {stream_info.name()}")
        self.plot_tab.add_stream(stream_info)
        self.log(f"Added stream to plot: {stream_info.name()} ({stream_info.type()})")

    def on_remove_stream(self, stream_info):
        print(f"[DASHBOARD DEBUG] on_remove_stream called for: {stream_info.name()}")
        self.plot_tab.remove_stream(stream_info)
        self.log(f"Removed stream from plot: {stream_info.name()} ({stream_info.type()})")

    # -----------------------------------------------------------
    # Plot Tab Integration
    # -----------------------------------------------------------
    def log_all_streams_removed(self):
        self.log("Removed all streams from plot.")

    def handle_all_streams_removed(self):
        """Handle cleanup when all streams are removed from plot."""
        print("[Dashboard] Cleaning up after all streams removed...")
        # Clear the LSL fetcher cache to ensure fresh discovery
        self.lsl_fetcher.clear_cache()
        print("[Dashboard] LSL fetcher cache cleared")

    def handle_tab_changed(self, index):
        """OPTIMIZED: Debounced tab change handler to reduce lag."""
        # Store the pending tab index and start debounce timer
        self.pending_tab_index = index
        self.tab_change_timer.start()

        # Immediately update visibility for performance (don't wait for debounce)
        current_widget = self.tabs.widget(index)
        if current_widget == self.plot_tab:
            self.plot_tab.set_visible(True)
        else:
            self.plot_tab.set_visible(False)

    def _handle_tab_changed_delayed(self):
        """OPTIMIZED: Delayed handler after debounce (reduces rapid switching lag)."""
        if self.pending_tab_index is None:
            return

        index = self.pending_tab_index
        current_widget = self.tabs.widget(index)

        if current_widget == self.plot_tab:
            # If user switched TO the Plot tab, unpause
            self.plot_tab.is_paused = False
            self.plot_tab.pause_button.setText("Pause")
            # REMOVED: Auto-discovery on every tab switch (user can manually add streams)
        else:
            # If user switched AWAY from the Plot tab, pause
            self.plot_tab.is_paused = True
            self.plot_tab.pause_button.setText("Resume")

    def _auto_add_streams(self):
        """
        Auto-discover available LSL streams and add them to the plot if they're not already there.
        This is called when switching to the Plot tab to ensure connected sensors are automatically visualized.
        """
        # Get available LSL streams
        available_streams = self.lsl_fetcher.get_available_streams()

        # Get the set of streams already being plotted
        streams_in_plot = self.lsl_browser.streams_in_plot

        # Auto-add any streams that aren't already being plotted
        for stream_info in available_streams:
            # Create unique ID matching the LSL browser's format
            hostname_part = stream_info.hostname() or "UnknownHost"
            name_part = stream_info.name() or "noname"
            type_part = stream_info.type() or "notype"
            uid_part = stream_info.uid() or "nouid"
            src_part = stream_info.source_id() or "nosrc"
            ch_part = str(stream_info.channel_count())
            unique_id = f"[{hostname_part}] {name_part}-{type_part}-{ch_part}-{uid_part}-{src_part}"

            # Only add streams from our sensors (Muse, Polar H10, or known types)
            stream_name = stream_info.name()
            stream_type = stream_info.type()

            # Check if this is a sensor stream we should auto-add
            is_sensor_stream = (
                "Muse" in stream_name or
                "Polar" in stream_name or
                stream_type in ["EEG", "ECG", "PPG", "GYRO", "Accelerometer"]
            )

            if is_sensor_stream and unique_id not in streams_in_plot:
                # Add to plot
                self.plot_tab.add_stream(stream_info)
                streams_in_plot.add(unique_id)
                self.log(f"Auto-added stream: {stream_info.name()} ({stream_info.type()})")

        # Refresh the LSL browser to update the UI highlighting
        self.lsl_browser.refresh_streams()

    # -----------------------------------------------------------
    # Stream Discovery
    # -----------------------------------------------------------
    def on_discover_streams_from_plot(self):
        """
        Handle discover streams request from plot tab.
        Uses async discovery and auto-adds all sensor streams.
        """
        print("[Dashboard] Discovering streams for plot...")
        self.log("Discovering LSL streams...")

        # Use async discovery with callback (OPTIMIZED: minimal wait time for instant discovery)
        self.lsl_fetcher.get_available_streams_async(
            callback=self._on_streams_discovered_for_plot,
            wait_time=0.1
        )

    def _on_streams_discovered_for_plot(self, streams):
        """Callback when async stream discovery completes - auto-add ALL streams to plot."""
        print(f"[Dashboard] Discovery complete: {len(streams)} streams found")
        self.log(f"Found {len(streams)} LSL stream(s)")

        # Get the set of streams already being plotted
        streams_in_plot = self.lsl_browser.streams_in_plot.copy()

        # Auto-add ALL discovered streams (not just sensor streams)
        added_count = 0
        for stream_info in streams:
            # Create unique ID matching the LSL browser's format
            hostname_part = stream_info.hostname() or "UnknownHost"
            name_part = stream_info.name() or "noname"
            type_part = stream_info.type() or "notype"
            uid_part = stream_info.uid() or "nouid"
            src_part = stream_info.source_id() or "nosrc"
            ch_part = str(stream_info.channel_count())
            unique_id = f"[{hostname_part}] {name_part}-{type_part}-{ch_part}-{uid_part}-{src_part}"

            # Add ALL streams that aren't already plotted
            if unique_id not in streams_in_plot:
                # Add to plot
                print(f"[Dashboard] Adding stream to plot: {stream_info.name()} ({stream_info.type()})")
                self.plot_tab.add_stream(stream_info)
                streams_in_plot.add(unique_id)
                self.log(f"Added stream: {stream_info.name()} ({stream_info.type()})")
                added_count += 1
            else:
                print(f"[Dashboard] Stream already in plot: {stream_info.name()}")

        # Update the LSL browser's tracking set
        self.lsl_browser.streams_in_plot = streams_in_plot

        # Refresh the LSL browser to update UI highlighting
        self.lsl_browser.refresh_streams()

        if added_count == 0:
            self.log("No new streams to add (all discovered streams already plotted)")
        else:
            self.log(f"Added {added_count} stream(s) to plot")

    # -----------------------------------------------------------
    # Logging
    # -----------------------------------------------------------
    def log(self, message):
        self.log_text.append(message)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("IXR Labs Suite")

        # Make window responsive to screen size (cross-platform compatible)
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()

        # Set initial size to 80% of screen width and 85% of screen height
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.85)

        # Center the window on screen
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2

        self.setGeometry(x, y, width, height)

        # Set minimum size to prevent window from becoming too small
        self.setMinimumSize(1000, 700)

        self.dashboard = Dashboard()
        self.setCentralWidget(self.dashboard)

    def closeEvent(self, event):
        # Gracefully disconnect Muse and Polar if still connected
        self.dashboard.muse_sensor.kill_publisher()
        self.dashboard.disconnect_muse()
        self.dashboard.disconnect_polar()
        super(MainWindow, self).closeEvent(event)
