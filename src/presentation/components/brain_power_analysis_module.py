"""
Brain Power Analysis Module - Presentation component for brain power analysis.

This module provides the UI for brain power analysis, showing brain power metrics
and EEG band powers with start/stop control. Uses BrainFlow directly instead of LSL.
"""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QMessageBox)

from src.presentation.components.brain_power_settings_dialog import BrainPowerSettingsDialog
from src.application.services.brain_power_worker import BrainPowerWorker
from gui.modern_theme import ModernTheme


class BrainPowerAnalysisModule(QWidget):
    """
    Brain Power Analysis Module based on the original IXR Suite.
    Shows brain power metrics and EEG band powers with start/stop control.
    Uses BrainFlow directly instead of LSL.
    """

    def __init__(self, parent=None, sensor=None, board_shim=None):
        super().__init__(parent)

        # Store sensor and board_shim references
        self.sensor = sensor
        self.board_shim = board_shim

        # Default settings (match original IXR-Suite)
        self.default_settings = {
            "calib_length": 600,
            "power_length": 10,
            "scale": 1.5,           # Match original IXR-Suite
            "offset": 0.5,          # Match original IXR-Suite
            "head_impact": 0.2,
            "longerterm_length": 30,
            "reference": "mean"     # Match original IXR-Suite
        }
        self.settings = self.default_settings.copy()

        # Worker thread
        self.worker = None

        # Ring buffers for temporal data (store last 100 points)
        self.max_history = 100
        self.short_term_history = []
        self.long_term_history = []
        self.final_power_history = []

        # UI setup
        self.init_ui()

    def handle_status_update(self, status_msg):
        """Handle status updates from worker thread."""
        self.status_label.setText(f"Status: {status_msg}")
        if "ERROR" in status_msg:
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 500;
                color: {ModernTheme.COLORS['danger']};
                padding: 12px 16px;
                background: {ModernTheme.COLORS['bg_secondary']};
                border-radius: 8px;
            """)
        elif "Running" in status_msg or "Connected" in status_msg:
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 500;
                color: {ModernTheme.COLORS['success']};
                padding: 12px 16px;
                background: {ModernTheme.COLORS['bg_secondary']};
                border-radius: 8px;
            """)
        else:
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 500;
                color: {ModernTheme.COLORS['warning']};
                padding: 12px 16px;
                background: {ModernTheme.COLORS['bg_secondary']};
                border-radius: 8px;
            """)

    def init_ui(self):
        """Initialize the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.setLayout(layout)

        # Apply modern theme
        self.setStyleSheet(ModernTheme.get_widget_style())

        # ===== HEADER CARD =====
        header_card = QWidget()
        header_card.setStyleSheet(ModernTheme.get_card_style())
        header_card_layout = QVBoxLayout(header_card)
        header_card_layout.setContentsMargins(12, 12, 12, 12)
        header_card_layout.setSpacing(10)

        # Title
        self.title_label = QLabel("Brain Power Analysis")
        self.title_label.setStyleSheet(ModernTheme.get_label_style('title'))
        header_card_layout.addWidget(self.title_label)

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.start_button = QPushButton("Start Analysis")
        self.start_button.setStyleSheet(ModernTheme.get_button_style('primary'))
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Analysis")
        self.stop_button.setStyleSheet(ModernTheme.get_button_style('danger'))
        self.stop_button.setMinimumHeight(40)
        self.stop_button.clicked.connect(self.stop_analysis)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setStyleSheet(ModernTheme.get_button_style('secondary'))
        self.settings_button.setMinimumHeight(40)
        self.settings_button.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_button)

        header_card_layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Status: Not running")
        self.status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {ModernTheme.COLORS['text_secondary']};
            padding: 12px 16px;
            background: {ModernTheme.COLORS['bg_secondary']};
            border-radius: 8px;
        """)
        header_card_layout.addWidget(self.status_label)

        layout.addWidget(header_card)

        # Apply modern theme to PyQtGraph
        ModernTheme.apply_pyqtgraph_theme()

        # ===== TEMPORAL METRICS CARD =====
        temporal_card = QWidget()
        temporal_card.setStyleSheet(ModernTheme.get_card_style())
        temporal_card_layout = QVBoxLayout(temporal_card)
  

        # Card title
        temporal_title = QLabel("Brain Power Metrics - Temporal Evolution")
        temporal_title.setStyleSheet(ModernTheme.get_label_style('title'))
        temporal_card_layout.addWidget(temporal_title)

        # Brain Power Metrics Plot
        self.power_plot = pg.PlotWidget()
        self.power_plot.setTitle("")  # Remove duplicate title since we have card title
        self.power_plot.showAxis('left', True)
        self.power_plot.setMenuEnabled('left', False)
        self.power_plot.showAxis('bottom', True)
        self.power_plot.setMenuEnabled('bottom', False)
        self.power_plot.setYRange(-0.1, 1.1, padding=0)
        # Set fixed height to ensure visibility in card layout
        self.power_plot.setMinimumHeight(300)
        self.power_plot.setMaximumHeight(500)
        self.power_plot.setLabel('left', 'Power', **{'font-size': '13px', 'font-weight': 'bold'})
        self.power_plot.setLabel('bottom', 'Time (samples)', **{'font-size': '13px', 'font-weight': 'bold'})

        # Apply modern theme styling
        ModernTheme.style_plot_widget(self.power_plot)

        # Explicitly set stylesheet to prevent card style inheritance
        self.power_plot.setStyleSheet("background: white;")

        # Add legend with modern styling BEFORE creating plots
        legend = self.power_plot.addLegend(offset=(10, 10))
        legend.setLabelTextSize('13px')

        # Create three line plots for temporal data with modern colors
        # Create in reverse order so short-term is on top (drawn last)
        # Use dashed line for short-term to make it always visible even when overlapping
        self.long_term_curve = self.power_plot.plot(
            pen=pg.mkPen(color=ModernTheme.COLORS['accent_cyan'], width=2),
            name='Long-term'
        )
        self.final_power_curve = self.power_plot.plot(
            pen=pg.mkPen(color=ModernTheme.COLORS['success'], width=3),
            name='Final Power'
        )
        self.short_term_curve = self.power_plot.plot(
            pen=pg.mkPen(color=ModernTheme.COLORS['accent_blue'], width=2, style=pg.QtCore.Qt.DashLine),
            name='Short-term'
        )

        temporal_card_layout.addWidget(self.power_plot, stretch=1)
        layout.addWidget(temporal_card)

        # ===== FREQUENCY BAND POWERS CARD =====
        band_card = QWidget()
        band_card.setStyleSheet(ModernTheme.get_card_style())
        band_card_layout = QVBoxLayout(band_card)
        band_card_layout.setContentsMargins(12, 12, 12, 12)

        # Card title
        band_title = QLabel("EEG Frequency Band Powers")
        band_title.setStyleSheet(ModernTheme.get_label_style('title'))
        band_card_layout.addWidget(band_title)

        # EEG Band Powers Plot
        self.band_plot = pg.PlotWidget()
        self.band_plot.setTitle("")  # Remove duplicate title since we have card title
        self.band_plot.showAxis('left', True)
        self.band_plot.setMenuEnabled('left', False)
        self.band_plot.showAxis('bottom', True)
        self.band_plot.setMenuEnabled('bottom', False)
        self.band_plot.setXRange(0.1, 5.9, padding=0)
        self.band_plot.setYRange(-0.1, 50, padding=0)
        # Set fixed height to ensure visibility in card layout
        self.band_plot.setMinimumHeight(300)
        self.band_plot.setMaximumHeight(500)
        self.band_plot.setLabel('left', 'Power (μV²)', **{'font-size': '13px', 'font-weight': 'bold'})
        self.band_plot.setLabel('bottom', 'Frequency Band', **{'font-size': '13px', 'font-weight': 'bold'})

        # Apply modern theme styling
        ModernTheme.style_plot_widget(self.band_plot)

        # Explicitly set stylesheet to prevent card style inheritance
        self.band_plot.setStyleSheet("background: white;")

        # Create bar graph for band powers with vibrant colors
        x_bands = [1, 2, 3, 4, 5]
        y_bands = [5, 5, 5, 5, 5]

        # Create modern professional colors for each bar (store as instance variable to preserve during updates)
        self.bar_colors = [
            ModernTheme.COLORS['eeg_1'],  # Delta - Blue
            ModernTheme.COLORS['eeg_2'],  # Theta - Cyan
            ModernTheme.COLORS['eeg_3'],  # Alpha - Green
            ModernTheme.COLORS['eeg_4'],  # Beta - Amber
            ModernTheme.COLORS['eeg_5'],  # Gamma - Purple
        ]

        self.band_bar = pg.BarGraphItem(x=x_bands, height=y_bands, width=0.7, brushes=self.bar_colors)
        self.band_plot.addItem(self.band_bar)

        # Set x-axis labels for bands with better spacing
        band_ticklabels = ['', 'Delta\n(0.5-4 Hz)', 'Theta\n(4-8 Hz)', 'Alpha\n(8-13 Hz)', 'Beta\n(13-30 Hz)', 'Gamma\n(30+ Hz)']
        band_tickdict = dict(enumerate(band_ticklabels))
        band_ax = self.band_plot.getAxis('bottom')
        band_ax.setTicks([band_tickdict.items()])

        band_card_layout.addWidget(self.band_plot, stretch=1)
        layout.addWidget(band_card)

        # ===== CURRENT VALUES CARD =====
        values_card = QWidget()
        values_card.setStyleSheet(ModernTheme.get_card_style())
        values_card_layout = QVBoxLayout(values_card)
        values_card_layout.setContentsMargins(12, 12, 12, 12)
        values_card_layout.setSpacing(10)

        # Card title
        values_title = QLabel("Current Values")
        values_title.setStyleSheet(ModernTheme.get_label_style('title'))
        values_card_layout.addWidget(values_title)

        # Current values display - Modern metric cards
        values_layout = QHBoxLayout()
     

        # Create modern metric cards with better visual hierarchy
        self.final_power_label = QLabel("Final Power\n0.00")
        self.final_power_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: 700;
                color: {ModernTheme.COLORS['text_primary']};
                letter-spacing: 0.3px;
                padding: 10px;
                background: {ModernTheme.COLORS['bg_primary']};
                border-radius: 12px;
                border: 2px solid {ModernTheme.COLORS['success']};
            }}
        """)
        self.final_power_label.setAlignment(Qt.AlignCenter)
        values_layout.addWidget(self.final_power_label)

        self.short_term_label = QLabel("Short-term\n0.00")
        self.short_term_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: 600;
                color: {ModernTheme.COLORS['text_primary']};
                padding: 10px;
                background: {ModernTheme.COLORS['bg_primary']};
                border-radius: 12px;
                border: 2px solid {ModernTheme.COLORS['accent_blue']};
            }}
        """)
        self.short_term_label.setAlignment(Qt.AlignCenter)
        values_layout.addWidget(self.short_term_label)

        self.long_term_label = QLabel("Long-term\n0.00")
        self.long_term_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: 600;
                color: {ModernTheme.COLORS['text_primary']};
                padding: 10px;
                background: {ModernTheme.COLORS['bg_primary']};
                border-radius: 12px;
                border: 2px solid {ModernTheme.COLORS['accent_cyan']};
            }}
        """)
        self.long_term_label.setAlignment(Qt.AlignCenter)
        values_layout.addWidget(self.long_term_label)

        values_card_layout.addLayout(values_layout)
        layout.addWidget(values_card)

    def start_analysis(self):
        """Start the brain power analysis after showing settings dialog."""
        # Get board_shim from sensor or use direct board_shim
        board_shim = None

        if self.sensor is not None:
            # Try to get board_shim from sensor
            if hasattr(self.sensor, 'handler') and self.sensor.handler is not None:
                if hasattr(self.sensor.handler, 'board'):
                    board_shim = self.sensor.handler.board
        elif self.board_shim is not None:
            board_shim = self.board_shim

        # Check if we have a valid board_shim
        if board_shim is None:
            QMessageBox.warning(
                self,
                "No Board Connected",
                "Please connect to a sensor (Muse) first before starting brain power analysis."
            )
            return

        # Check if board is prepared
        if not board_shim.is_prepared():
            QMessageBox.warning(
                self,
                "Board Not Ready",
                "The sensor board is not ready. Please ensure the Muse is connected and streaming."
            )
            return

        # Show settings dialog first
        dlg = BrainPowerSettingsDialog(self, self.settings)
        if dlg.exec_():
            new_settings = dlg.get_settings()
            self.settings.update(new_settings)

            # Clear history buffers for new session
            self.short_term_history = []
            self.long_term_history = []
            self.final_power_history = []

            # Create and start worker with board_shim
            self.worker = BrainPowerWorker(self.settings, board_shim)
            self.worker.analysisUpdated.connect(self.handle_analysis_update)
            self.worker.statusUpdated.connect(self.handle_status_update)
            self.worker.start()

            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 500;
                color: {ModernTheme.COLORS['success']};
                padding: 12px 16px;
                background: {ModernTheme.COLORS['bg_secondary']};
                border-radius: 8px;
            """)

    def stop_analysis(self):
        """Stop the brain power analysis."""
        if self.worker is not None:
            self.worker.stop()
            self.worker = None

        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Status: Not running")
        self.status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {ModernTheme.COLORS['text_secondary']};
            padding: 12px 16px;
            background: {ModernTheme.COLORS['bg_secondary']};
            border-radius: 8px;
        """)

    def open_settings(self):
        """Open settings dialog to modify parameters."""
        if self.worker is not None:
            # Analysis is running, show warning
            reply = QMessageBox.question(
                self,
                "Analysis Running",
                "Analysis is currently running. Opening settings will stop the analysis. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_analysis()
            else:
                return

        # Show settings dialog
        dlg = BrainPowerSettingsDialog(self, self.settings)
        if dlg.exec_():
            new_settings = dlg.get_settings()
            self.settings.update(new_settings)

    def handle_analysis_update(self, final_power, short_term, long_term, band_powers):
        """Handle analysis update from worker thread."""
        # Append new values to history
        self.short_term_history.append(short_term)
        self.long_term_history.append(long_term)
        self.final_power_history.append(final_power)

        # Maintain maximum history length (ring buffer)
        if len(self.short_term_history) > self.max_history:
            self.short_term_history.pop(0)
        if len(self.long_term_history) > self.max_history:
            self.long_term_history.pop(0)
        if len(self.final_power_history) > self.max_history:
            self.final_power_history.pop(0)

        # Update line plots with temporal data
        x = list(range(len(self.short_term_history)))
        self.short_term_curve.setData(x, self.short_term_history)
        self.long_term_curve.setData(x, self.long_term_history)
        self.final_power_curve.setData(x, self.final_power_history)

        # Update band powers bar chart with minimum height to ensure visibility
        # Handle NaN/Inf values and ensure all bars are visible
        import numpy as np

        # Clean the band power data
        clean_band_powers = []
        for bp in band_powers:
            if np.isnan(bp) or np.isinf(bp) or bp < 0:
                clean_band_powers.append(0.1)  # Use small positive value for invalid data
            else:
                clean_band_powers.append(float(bp))

        # Calculate dynamic minimum height (5% of max value, or 1.0 minimum)
        max_power = max(clean_band_powers) if clean_band_powers else 10.0
        min_height = max(max_power * 0.05, 1.0)

        # Apply minimum height to ensure visibility
        visible_band_powers = [max(bp, min_height) for bp in clean_band_powers]

        # Update bar chart (IMPORTANT: preserve brushes to maintain colors)
        self.band_bar.setOpts(height=visible_band_powers, brushes=self.bar_colors)

        # Dynamically adjust Y-axis range with 10% padding
        y_max = max(visible_band_powers) * 1.1
        self.band_plot.setYRange(0, y_max, padding=0)

        # Update text labels with multi-line format
        self.final_power_label.setText(f"Final Power\n{final_power:.3f}")
        self.short_term_label.setText(f"Short-term\n{short_term:.3f}")
        self.long_term_label.setText(f"Long-term\n{long_term:.3f}")

    def closeEvent(self, event):
        """Handle widget close event."""
        if self.worker is not None:
            self.worker.stop()
        super().closeEvent(event)
