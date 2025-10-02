# focus_analysis_module.py

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
                             QPushButton, QDialog, QDialogButtonBox, QFormLayout,
                             QListWidget, QListWidgetItem)
from pylsl import resolve_byprop, StreamInlet
from scipy.signal import butter, filtfilt, welch, detrend
import time

# ---------------------------
# Popup Settings Dialog
# ---------------------------
class FocusSettingsDialog(QDialog):
    """Popup dialog to configure Focus Analysis settings."""
    def __init__(self, parent=None, eeg_channels=None, gyro_channels=None, default_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Focus Analysis Settings")
        # Use provided channel lists; for gyro, assume they are already filtered.
        self.default_settings = default_settings or {
            "bandpass_low": 1.0,
            "bandpass_high": 59.0,
            "notch_low": 48.0,
            "notch_high": 52.0,
            "baseline_duration": 1.5,
            "head_impact": 0.2,
            "eeg_channels": eeg_channels if eeg_channels is not None else [],
            "gyro_channels": gyro_channels if gyro_channels is not None else []
        }
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout(self)
        
        self.bp_low_spin = QDoubleSpinBox()
        self.bp_low_spin.setRange(0.1, 20)
        self.bp_low_spin.setValue(self.default_settings["bandpass_low"])
        layout.addRow("EEG Bandpass Low (Hz):", self.bp_low_spin)
        
        self.bp_high_spin = QDoubleSpinBox()
        self.bp_high_spin.setRange(10, 100)
        self.bp_high_spin.setValue(self.default_settings["bandpass_high"])
        layout.addRow("EEG Bandpass High (Hz):", self.bp_high_spin)
        
        self.notch_low_spin = QDoubleSpinBox()
        self.notch_low_spin.setRange(40, 50)
        self.notch_low_spin.setValue(self.default_settings["notch_low"])
        layout.addRow("Notch Low (Hz):", self.notch_low_spin)
        
        self.notch_high_spin = QDoubleSpinBox()
        self.notch_high_spin.setRange(50, 60)
        self.notch_high_spin.setValue(self.default_settings["notch_high"])
        layout.addRow("Notch High (Hz):", self.notch_high_spin)
        
        self.baseline_spin = QDoubleSpinBox()
        self.baseline_spin.setRange(0.5, 10)
        self.baseline_spin.setValue(self.default_settings["baseline_duration"])
        layout.addRow("Baseline Duration (s):", self.baseline_spin)
        
        self.head_impact_spin = QDoubleSpinBox()
        self.head_impact_spin.setRange(0.0, 1.0)
        self.head_impact_spin.setValue(self.default_settings["head_impact"])
        layout.addRow("Head Impact Weight:", self.head_impact_spin)
        
        self.eeg_list = QListWidget()
        for ch in self.default_settings["eeg_channels"]:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.eeg_list.addItem(item)
        layout.addRow("EEG Channels:", self.eeg_list)
        
        self.gyro_list = QListWidget()
        for ch in self.default_settings["gyro_channels"]:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.gyro_list.addItem(item)
        layout.addRow("Gyro Channels:", self.gyro_list)
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
    
    def get_settings(self):
        eeg_channels = []
        for i in range(self.eeg_list.count()):
            item = self.eeg_list.item(i)
            if item.checkState() == Qt.Checked:
                eeg_channels.append(item.text())
        gyro_channels = []
        for i in range(self.gyro_list.count()):
            item = self.gyro_list.item(i)
            if item.checkState() == Qt.Checked:
                gyro_channels.append(item.text())
        return {
            "bandpass_low": self.bp_low_spin.value(),
            "bandpass_high": self.bp_high_spin.value(),
            "notch_low": self.notch_low_spin.value(),
            "notch_high": self.notch_high_spin.value(),
            "baseline_duration": self.baseline_spin.value(),
            "head_impact": self.head_impact_spin.value(),
            "eeg_channels": eeg_channels,
            "gyro_channels": gyro_channels
        }

# ---------------------------
# Focus Analysis Worker Thread
# ---------------------------
class FocusAnalysisWorker(QThread):
    # Signal emitting (final_focus, metric_history)
    analysisUpdated = pyqtSignal(float, list)
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._running = True
        self.metric_history = []
        self.eeg_inlet = None
        self.gyro_inlet = None
        self.available_eeg_channels = []
        self.available_gyro_channels = []
        self.eeg_sr = 256.0
        self.gyro_sr = 50.0

    def resolve_streams(self):
        from pylsl import resolve_byprop, StreamInlet
        # Resolve EEG streams using type "EEG"
        eeg_infos = resolve_byprop("type", "EEG", minimum=1, timeout=10)
        gyro_infos = resolve_byprop("type", "GYRO", minimum=1, timeout=10)
        if eeg_infos:
            self.eeg_inlet = StreamInlet(eeg_infos[0])
            self.eeg_sr = float(self.eeg_inlet.info().nominal_srate())
        else:
            self.eeg_inlet = None
        if gyro_infos:
            self.gyro_inlet = StreamInlet(gyro_infos[0])
            self.gyro_sr = float(self.gyro_inlet.info().nominal_srate())
        else:
            self.gyro_inlet = None
        # Extract channel names using our updated helper:
        self.available_eeg_channels = self._extract_channel_names(eeg_infos[0]) if eeg_infos else []
        # Filter EEG channels: include only those that contain "eeg" (case-insensitive)
        self.available_eeg_channels = [ch for ch in self.available_eeg_channels if "eeg" in ch.lower()]
        self.available_gyro_channels = self._extract_channel_names(gyro_infos[0]) if gyro_infos else []
        # For gyro, include only channels containing "gyro"
        self.available_gyro_channels = [ch for ch in self.available_gyro_channels if "gyro" in ch.lower()]

    def _extract_channel_names(self, stream_info):
        # Use the updated method provided by the user.
        inlet = StreamInlet(stream_info)
        full_info = inlet.info()
        desc = full_info.desc()
        if desc is None or desc.child("channels").empty():
            return []
        names = []
        chan = desc.child("channels").child("channel")
        while not chan.empty():
            label = chan.child_value("label")
            if not label:
                label = chan.child_value("name") or "Ch"
            names.append(label)
            chan = chan.next_sibling("channel")
        return names

    def run(self):
        while self._running:
            # Ensure we have valid inlets
            if self.eeg_inlet is None or self.gyro_inlet is None:
                self.resolve_streams()
                self.msleep(500)
                continue

            # Pull a chunk from EEG
            eeg_sr = self.eeg_sr
            num_samples = int(self.settings["baseline_duration"] * eeg_sr)
            samples, timestamps = self.eeg_inlet.pull_chunk(timeout=0.0, max_samples=num_samples)
            if not timestamps or len(samples) < 1:
                continue
            eeg_data = np.array(samples, dtype=float).T  # shape: (channels, samples)
            # Select only channels as per settings:
            selected_indices = [i for i, ch in enumerate(self.available_eeg_channels)
                                if ch in self.settings["eeg_channels"]]
            if len(selected_indices) == 0:
                avg_focus = 0.0
            else:
                selected_eeg = eeg_data[selected_indices, :]
                selected_eeg = detrend(selected_eeg, axis=1)
                b_bp, a_bp = butter(2, [self.settings["bandpass_low"]/(eeg_sr/2),
                                         self.settings["bandpass_high"]/(eeg_sr/2)], btype='band')
                eeg_bp = filtfilt(b_bp, a_bp, selected_eeg, axis=1)
                b_notch, a_notch = butter(2, [self.settings["notch_low"]/(eeg_sr/2),
                                              self.settings["notch_high"]/(eeg_sr/2)], btype='bandstop')
                eeg_notched = filtfilt(b_notch, a_notch, eeg_bp, axis=1)
                nfft = 2**int(np.floor(np.log2(num_samples)))
                focus_values = []
                for ch in eeg_notched:
                    freq, psd = welch(ch, fs=eeg_sr, nperseg=nfft)
                    def band_power(low, high):
                        idx = np.logical_and(freq >= low, freq <= high)
                        return np.mean(psd[idx]) if np.any(idx) else 0.0
                    theta = band_power(4, 8)
                    alpha = band_power(8, 13)
                    beta  = band_power(13, 30)
                    gamma = band_power(30, 60)
                    if (theta + alpha) == 0 or gamma == 0:
                        focus_val = 0.0
                    else:
                        focus_val = (beta / (theta + alpha)) / gamma
                    focus_values.append(focus_val)
                avg_focus = np.mean(focus_values) if focus_values else 0.0

            # Gyro processing:
            head_movement = 0.0
            if self.gyro_inlet is not None:
                gyro_sr = self.gyro_sr
                num_samples_gyro = int(self.settings["baseline_duration"] * gyro_sr)
                gyro_samples, _ = self.gyro_inlet.pull_chunk(timeout=0.0, max_samples=num_samples_gyro)
                if gyro_samples is not None and len(gyro_samples) > 0:
                    gyro_data = np.array(gyro_samples, dtype=float)
                    head_movement = np.mean(np.abs(gyro_data))
                    head_movement = np.clip(head_movement / 50.0, 0, 1)
            
            final_focus = avg_focus + (1 - head_movement) * self.settings["head_impact"]
            self.metric_history.append(final_focus)
            if len(self.metric_history) > 100:
                self.metric_history = self.metric_history[-100:]
            self.analysisUpdated.emit(final_focus, self.metric_history)
            self.msleep(200)
    
    def stop(self):
        self._running = False
        self.quit()
        self.wait()

# ---------------------------
# Focus Analysis Module (GUI)
# ---------------------------
class FocusAnalysisModule(QWidget):
    """
    A QWidget hosting focus analysis.
    It starts a FocusAnalysisWorker (a QThread) that performs processing using
    real Muse LSL data (EEG and Gyro) and updates the GUI.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.default_settings = {
            "bandpass_low": 1.0,
            "bandpass_high": 59.0,
            "notch_low": 48.0,
            "notch_high": 52.0,
            "baseline_duration": 1.5,
            "head_impact": 0.2,
            "eeg_channels": [],  # will be updated when settings open
            "gyro_channels": []  # likewise
        }
        self.settings = self.default_settings.copy()
        self.metric_history = []
        self.worker = FocusAnalysisWorker(self.settings)
        self.worker.analysisUpdated.connect(self.handle_analysis_update)
        self.worker.start()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Focus Analysis")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)
        
        self.plot_widget = pg.PlotWidget(title="Focus Metric History")
        self.plot_widget.setLabel('left', 'Focus')
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.focus_curve = self.plot_widget.plot([], [], pen=pg.mkPen('r', width=2))
        layout.addWidget(self.plot_widget)
        
        self.focus_label = QLabel("Current Focus: 0.00")
        self.focus_label.setAlignment(Qt.AlignCenter)
        self.focus_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.focus_label)
    
    def open_settings(self):
        # Resolve streams before opening settings.
        self.worker.resolve_streams()
        dlg = FocusSettingsDialog(self,
                                  eeg_channels=self.worker.available_eeg_channels,
                                  gyro_channels=self.worker.available_gyro_channels,
                                  default_settings=self.settings)
        if dlg.exec_():
            new_settings = dlg.get_settings()
            self.settings.update(new_settings)
            self.worker.settings = self.settings  # update worker settings
    
    def handle_analysis_update(self, focus, history):
        self.focus_label.setText(f"Current Focus: {focus:.2f}")
        self.metric_history = history
        x = np.arange(len(self.metric_history)) / 5.0  # assuming update rate 5 Hz
        self.focus_curve.setData(x, np.array(self.metric_history))
    
    def closeEvent(self, event):
        self.worker.stop()
        super().closeEvent(event)
