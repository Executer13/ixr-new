# dashboard.py

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QTabWidget,
    QLabel, QGridLayout
)
from PyQt5.QtCore import Qt
from sensors.muse_sensor import MuseSensor
from sensors.polar_sensor import PolarSensor
from gui.lsl_browser_widget import LSLBrowserWidget
from gui.plot_tab import PlotTab
from sensors.lsl_fetcher import LSLFetcher
from processing.focus_analysis_module import FocusAnalysisModule

def set_indicator(label_circle: QLabel, label_text: QLabel, status_text: str, color: str):
    """
    Update two parts of an indicator:
      1) label_circle: a tiny circle with the given color
      2) label_text: textual status (e.g., "Connected", "Disconnected", etc.)
    """
    label_text.setText(status_text)
    label_circle.setStyleSheet(
        f"""
        border-radius: 5px;
        min-width: 10px; 
        min-height: 10px; 
        max-width: 10px;
        max-height: 10px;
        background-color: {color};
        margin-right: 6px;
        """
    )

class Dashboard(QWidget):
    def __init__(self, parent=None):
        super(Dashboard, self).__init__(parent)
        self.muse_sensor = MuseSensor()
        self.polar_sensor = PolarSensor()
        self.lsl_fetcher = LSLFetcher()
        self.init_ui()

        self.muse_sensor.status_changed.connect(self.handle_muse_status_update)
        self.polar_sensor.status_changed.connect(self.handle_polar_status_update)
        self.tabs.currentChanged.connect(self.handle_tab_changed)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # =========== Sensors Tab ============
        sensors_tab = QWidget()
        sensors_layout = QVBoxLayout(sensors_tab)

        #
        # MUSE Controls
        #
        muse_button_layout = QHBoxLayout()
        self.muse_connect_button = QPushButton("Connect Muse")
        self.muse_disconnect_button = QPushButton("Disconnect Muse")
        muse_button_layout.addWidget(self.muse_connect_button)
        muse_button_layout.addWidget(self.muse_disconnect_button)
        sensors_layout.addLayout(muse_button_layout)

        # MUSE Indicators (2 rows: Connection, Streaming)
        self.muse_connection_circle = QLabel()
        self.muse_connection_text   = QLabel("Disconnected")
        self.muse_stream_circle     = QLabel()
        self.muse_stream_text       = QLabel("Not Streaming")
        set_indicator(self.muse_connection_circle, self.muse_connection_text, "Disconnected", "red")
        set_indicator(self.muse_stream_circle,     self.muse_stream_text,     "Not Streaming", "red")

        muse_status_layout = QGridLayout()
        muse_status_layout.addWidget(QLabel("Muse Connection:"), 0, 0, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_connection_circle, 0, 1, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_connection_text,   0, 2)

        muse_status_layout.addWidget(QLabel("Muse Stream:"),      1, 0, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_stream_circle,     1, 1, Qt.AlignRight)
        muse_status_layout.addWidget(self.muse_stream_text,       1, 2)

        sensors_layout.addLayout(muse_status_layout)

        #
        # POLAR Controls
        #
        polar_button_layout = QHBoxLayout()
        self.polar_connect_button = QPushButton("Connect Polar H10")
        self.polar_disconnect_button = QPushButton("Disconnect Polar H10")
        polar_button_layout.addWidget(self.polar_connect_button)
        polar_button_layout.addWidget(self.polar_disconnect_button)
        sensors_layout.addLayout(polar_button_layout)

        # POLAR Indicators
        self.polar_connection_circle = QLabel()
        self.polar_connection_text   = QLabel("Disconnected")
        self.polar_stream_circle     = QLabel()
        self.polar_stream_text       = QLabel("Not Streaming")
        set_indicator(self.polar_connection_circle, self.polar_connection_text, "Disconnected", "red")
        set_indicator(self.polar_stream_circle,     self.polar_stream_text,     "Not Streaming", "red")

        polar_status_layout = QGridLayout()
        polar_status_layout.addWidget(QLabel("Polar Connection:"), 0, 0, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_connection_circle, 0, 1, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_connection_text,   0, 2)

        polar_status_layout.addWidget(QLabel("Polar Stream:"),      1, 0, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_stream_circle,     1, 1, Qt.AlignRight)
        polar_status_layout.addWidget(self.polar_stream_text,       1, 2)

        sensors_layout.addLayout(polar_status_layout)

        #
        # LSL Browser in the same tab
        #
        lsl_title = QLabel("Available LSL Streams (double/right click to plot)")
        lsl_title.setStyleSheet("font-weight: bold;")
        sensors_layout.addWidget(lsl_title)

        self.lsl_browser = LSLBrowserWidget(self.lsl_fetcher)
        self.lsl_browser.add_stream_requested.connect(self.on_add_stream)
        self.lsl_browser.remove_stream_requested.connect(self.on_remove_stream)
        sensors_layout.addWidget(self.lsl_browser)

        #
        # Status/Log box
        #
        status_title = QLabel("Log / Status")
        status_title.setStyleSheet("font-weight: bold;")
        sensors_layout.addWidget(status_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        sensors_layout.addWidget(self.log_text)

        self.tabs.addTab(sensors_tab, "Sensors")

        # =========== Plot Tab ============
        self.plot_tab = PlotTab()
        self.tabs.addTab(self.plot_tab, "Plot")
        self.plot_tab.all_streams_removed.connect(self.lsl_browser.clear_all_plot_markers)
        self.plot_tab.all_streams_removed.connect(self.log_all_streams_removed)

        # =========== Analysis Tab ============
        self.analysis_widget = FocusAnalysisModule()
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
        self.plot_tab.add_stream(stream_info)
        self.log(f"Added stream to plot: {stream_info.name()} ({stream_info.type()})")

    def on_remove_stream(self, stream_info):
        self.plot_tab.remove_stream(stream_info)
        self.log(f"Removed stream from plot: {stream_info.name()} ({stream_info.type()})")

    # -----------------------------------------------------------
    # Plot Tab Integration
    # -----------------------------------------------------------
    def log_all_streams_removed(self):
        self.log("Removed all streams from plot.")

    def handle_tab_changed(self, index):
        # Check if the newly selected tab is the Plot tab
        current_widget = self.tabs.widget(index)
        if current_widget == self.plot_tab:
            # If user switched TO the Plot tab, unpause
            self.plot_tab.is_paused = False
            self.plot_tab.pause_button.setText("Pause")
        else:
            # If user switched AWAY from the Plot tab, pause
            self.plot_tab.is_paused = True
            self.plot_tab.pause_button.setText("Resume")

    # -----------------------------------------------------------
    # Logging
    # -----------------------------------------------------------
    def log(self, message):
        self.log_text.append(message)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("IXR Labs Suite")
        self.setGeometry(100, 100, 1400, 1200)
        self.dashboard = Dashboard()
        self.setCentralWidget(self.dashboard)

    def closeEvent(self, event):
        # Gracefully disconnect Muse and Polar if still connected
        self.dashboard.muse_sensor.kill_publisher()
        self.dashboard.disconnect_muse()
        self.dashboard.disconnect_polar()
        super(MainWindow, self).closeEvent(event)
