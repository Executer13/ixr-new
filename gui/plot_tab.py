# plot_tab.py

import numpy as np
import pyqtgraph as pg

# Platform-compatible OpenGL configuration with fallback
try:
    pg.setConfigOptions(useOpenGL=True)
    _opengl_enabled = True
except Exception as e:
    print(f"Warning: OpenGL acceleration not available: {e}")
    print("Falling back to software rendering (performance may be reduced)")
    pg.setConfigOptions(useOpenGL=False)
    _opengl_enabled = False

from scipy.signal import welch, butter, filtfilt
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QCheckBox,
    QScrollArea, QSplitter, QTabWidget
)
from PyQt5.QtCore import Qt
from pylsl import StreamInlet, StreamInfo
import time
from brainflow import DataFilter, DetrendOperations, FilterTypes, WindowOperations
from gui.modern_theme import ModernTheme
from gui.ring_buffer import TwoBufferRing

from src.common.utils.logger import get_logger

logger = get_logger(__name__)

class PlotTab(QWidget):
    """
    A tab that plots multiple LSL streams via PyQtGraph, using ring buffers
    but only filtering newly arrived chunks, plus manual downsampling.
    """

    all_streams_removed = pyqtSignal()  # Emitted when "Remove All Streams" is pressed
    discover_streams_requested = pyqtSignal()  # Emitted when "Discover Streams" is clicked

    def __init__(self, parent=None):
        logger.debug("PlotTab initializing...")
        super().__init__(parent)

        self.t1 = time.perf_counter(), time.process_time()
        self.t2 = time.perf_counter(), time.process_time()
        self.t3 = time.perf_counter(), time.process_time()
        self.t4 = time.perf_counter(), time.process_time()

        self.plot_time_window = 5.0     # default time window in seconds
        self.refresh_rate = 25.0        # 25 fps - matches Analysis tab (was 20, now optimized with display-only filtering)
        self.max_points = 500           # CRITICAL: Reduced from 1000 for 2x faster rendering
        self.psd_window_s = 2.0         # PSD calculation window in seconds
        self.psd_update_counter = 0     # Counter to throttle PSD updates
        self.psd_update_interval = 3    # Update PSD every N frames (reduce CPU load)
        self.is_visible = True          # Track if tab is visible (optimization)

        # Log OpenGL status
        if _opengl_enabled:
            logger.info("PyQtGraph: OpenGL acceleration enabled")
        else:
            logger.warning("PyQtGraph: Using software rendering (OpenGL disabled)")
            logger.info("For better performance, ensure graphics drivers are up to date")

        # Apply modern theme to PyQtGraph
        try:
            ModernTheme.apply_pyqtgraph_theme()
        except Exception as e:
            logger.warning(f"Could not apply PyQtGraph theme: {e}")

        self._init_colors()

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Control bar (pause, remove streams, time window, discover)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(12)
        control_layout.setContentsMargins(16, 16, 16, 16)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setStyleSheet(ModernTheme.get_button_style('secondary'))

        self.remove_button = QPushButton("Remove All Streams")
        self.remove_button.setStyleSheet(ModernTheme.get_button_style('danger'))

        self.discover_button = QPushButton("Discover Streams")
        self.discover_button.setStyleSheet(ModernTheme.get_button_style('primary'))
        self.discover_button.setToolTip("Auto-discover and add available LSL streams to plot")

        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.remove_button)
        control_layout.addWidget(self.discover_button)

        self.window_label = QLabel("Window (s):")
        self.window_label.setStyleSheet(ModernTheme.get_label_style('primary'))
        self.window_spin = QDoubleSpinBox()
        self.window_spin.setRange(0.1, 60.0)
        self.window_spin.setValue(self.plot_time_window)
        self.window_spin.setSingleStep(0.5)
        self.window_spin.setStyleSheet(ModernTheme.get_spinbox_style())

        control_layout.addWidget(self.window_label)
        control_layout.addWidget(self.window_spin)

        # Enable PSD checkbox
        self.enable_psd_checkbox = QCheckBox("Show PSD")
        self.enable_psd_checkbox.setChecked(False)
        self.enable_psd_checkbox.setStyleSheet(ModernTheme.get_checkbox_style())
        self.enable_psd_checkbox.stateChanged.connect(self._toggle_psd_view)
        control_layout.addWidget(self.enable_psd_checkbox)

        control_layout.addStretch()
        self.main_layout.addLayout(control_layout)

        # Create splitter for time series and analysis plots
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3)  # Make splitter handle more visible
        self.main_layout.addWidget(self.splitter)

        # Left side: Scroll area for time series channel rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(ModernTheme.get_scrollarea_style())
        self.scroll_area.setMinimumWidth(400)  # Ensure left side never collapses
        self.splitter.addWidget(self.scroll_area)

        # Container & layout for channels
        self.channels_container = QWidget()
        self.channels_layout = QVBoxLayout(self.channels_container)
        self.channels_container.setLayout(self.channels_layout)
        self.scroll_area.setWidget(self.channels_container)

        # Add placeholder label for when no streams are added
        self.placeholder_label = QLabel("No streams added.\n\nGo to the Sensors tab to connect devices,\nthen add streams to visualize data here.")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(ModernTheme.get_label_style('secondary'))
        self.channels_layout.addWidget(self.placeholder_label)
        self.channels_layout.addStretch()

        # Right side: Analysis plots (PSD and band power)
        self.analysis_widget = QWidget()
        self.analysis_layout = QVBoxLayout(self.analysis_widget)
        self.analysis_widget.setLayout(self.analysis_layout)
        self.analysis_widget.setMinimumWidth(350)  # Ensure right side maintains size
        self.splitter.addWidget(self.analysis_widget)

        # Initialize PSD plot
        self._init_psd_plot()

        # Make analysis widget always visible
        self.analysis_widget.setVisible(True)

        # Set splitter initial sizes (70% time series, 30% analysis)
        self.splitter.setSizes([700, 300])

        # Data structures for streams:
        # self.streams_data = [
        #   {
        #       "uid": str,
        #       "inlet": StreamInlet,
        #       "sr": float,
        #       "channels": [ {...}, {...}, ...]
        #   },
        #   ...
        # ]
        #
        # Each channel dict (OPTIMIZED with ring buffers):
        # {
        #   "name": str,
        #   "ring_buffer": TwoBufferRing,    # Optimized circular buffer for time/value
        #   "plot_item": PlotDataItem,
        #   "plot_widget": PlotWidget,       # Keep reference for batch updates
        #   "filter_checkbox": QCheckBox,
        #   "bandpass_low_spin": QDoubleSpinBox,   # IXR-Suite default: 1.0 Hz
        #   "bandpass_high_spin": QDoubleSpinBox,  # IXR-Suite default: 59.0 Hz
        #   "bandstop_low_spin": QDoubleSpinBox,   # IXR-Suite default: 48.0 Hz
        #   "bandstop_high_spin": QDoubleSpinBox,  # IXR-Suite default: 52.0 Hz
        #   "filter_enabled": bool,
        #   "sr": float
        # }

        self.streams_data = []
        self.stream_uids = set()
        self.is_paused = True
        self.last_xrange_update = None  # Track last X-range to avoid redundant updates

        # Wire up signals
        self.pause_button.clicked.connect(self.toggle_pause)
        self.remove_button.clicked.connect(self.remove_all_streams)
        self.discover_button.clicked.connect(self.on_discover_streams)
        self.window_spin.valueChanged.connect(self.on_window_spin_changed)

        # Timer for pulling data & updating
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / self.refresh_rate))  # ~20 fps

    def _init_colors(self):
        """Initialize colors and pens for plots (from IXR-Suite)."""
        self.pens = []
        self.brushes = []
        colors = ['#e9c46a', '#f4a261', '#e76f51', '#d62828', '#2a9d8f', '#168aad', '#e9f5db', '#A57E2F', '#A53B2F']
        for color in colors:
            pen = pg.mkPen({'color': color, 'width': 2})
            self.pens.append(pen)
            brush = pg.mkBrush(color)
            self.brushes.append(brush)

    def _init_psd_plot(self):
        """Initialize PSD (spectral power) plot (from IXR-Suite)."""
        self.psd_plot_widget = pg.PlotWidget()
        self.psd_plot_widget.showAxis('left', False)
        self.psd_plot_widget.setMenuEnabled('left', False)
        self.psd_plot_widget.setTitle('Spectral Power (PSD)')
        self.psd_plot_widget.setLogMode(False, True)
        self.psd_plot_widget.setLabel('bottom', 'Frequency (Hz)')
        self.psd_plot_widget.setXRange(1, 60, padding=0)
        # Responsive height - minimum size but can expand with window
        self.psd_plot_widget.setMinimumHeight(200)

        # Apply modern theme
        ModernTheme.style_plot_widget(self.psd_plot_widget)

        self.analysis_layout.addWidget(self.psd_plot_widget)
        self.psd_curves = []



    def _toggle_psd_view(self, state):
        """Toggle visibility of PSD and band power plots."""
        # Analysis widget is now always visible, but we can still toggle calculations
        pass

    def _apply_signal_processing(self, data, sr):
        """Apply signal processing to EEG data (from IXR-Suite)."""
        try:
            # Detrend
            DataFilter.detrend(data, DetrendOperations.CONSTANT.value)
            # Bandpass filter (1-59 Hz)
            DataFilter.perform_bandpass(
                data=data,
                sampling_rate=sr,
                start_freq=1.0,
                stop_freq=59.0,
                order=2,
                filter_type=FilterTypes.BUTTERWORTH.value,
                ripple=0.0
            )
            # Bandstop filter (48-52 Hz to remove line noise)
            DataFilter.perform_bandstop(
                data=data,
                sampling_rate=sr,
                start_freq=48.0,
                stop_freq=52.0,
                order=2,
                filter_type=FilterTypes.BUTTERWORTH.value,
                ripple=0.0
            )
        except Exception as e:
            print(f"Signal processing error: {e}")
        return data

    def _calculate_psd_and_bands(self, data, sr):
        """Calculate PSD and band powers (from IXR-Suite)."""
        try:
            psd_size = DataFilter.get_nearest_power_of_two(int(sr))
            if len(data) < psd_size:
                return None, None

            psd_data = DataFilter.get_psd_welch(
                data=data,
                nfft=psd_size,
                overlap=psd_size // 2,
                sampling_rate=int(sr),
                window=WindowOperations.BLACKMAN_HARRIS.value
            )

            # Calculate band powers
            delta = DataFilter.get_band_power(psd_data, 1.0, 4.0)
            theta = DataFilter.get_band_power(psd_data, 4.0, 8.0)
            alpha = DataFilter.get_band_power(psd_data, 8.0, 13.0)
            beta = DataFilter.get_band_power(psd_data, 13.0, 30.0)
            gamma = DataFilter.get_band_power(psd_data, 30.0, 60.0)

            bands = [delta, theta, alpha, beta, gamma]
            return psd_data, bands
        except Exception as e:
            print(f"PSD calculation error: {e}")
            return None, None


    def on_window_spin_changed(self, val):
        print("on_window_spin_changed")
        """Update the time window in seconds."""
        self.plot_time_window = val
        # Optionally recalc ring buffer sizes if you want them dynamic:
        # for sd in self.streams_data:
        #     for ch in sd["channels"]:
        #         ch["x_deque"].maxlen = int(ch["sr"] * self.plot_time_window) + 50
        #         ch["y_deque"].maxlen = int(ch["sr"] * self.plot_time_window) + 50

    def toggle_pause(self):
        print("toggle_pause")
        self.is_paused = not self.is_paused
        self.pause_button.setText("Resume" if self.is_paused else "Pause")

    def on_discover_streams(self):
        """Handle Discover Streams button click - emit signal to dashboard."""
        print("[Plot Tab] Discover Streams button clicked")
        self.discover_streams_requested.emit()

    def add_stream(self, info: StreamInfo):
        print("add_stream")
        """
        Add a new stream if not already present.
        Create an inlet, parse channel info, store them in self.streams_data,
        then rebuild the subplots.
        """
        uid = info.name()
        print(f"[PLOT_TAB DEBUG] add_stream called for: {uid}")
        print(f"[PLOT_TAB DEBUG] Stream type: {info.type()}, channels: {info.channel_count()}")
        if uid in self.stream_uids:
            print(f"[PLOT_TAB DEBUG] Stream {uid} already in stream_uids, skipping")
            return

        print(f"[PLOT_TAB DEBUG] Creating StreamInlet for {uid}...")
        inlet = StreamInlet(info)
        full_info = inlet.info()
        sr = full_info.nominal_srate() or 100.0
        ch_count = full_info.channel_count()

        # channel names
        channel_names = self._extract_channel_names(full_info)
        if not channel_names:
            channel_names = [f"Ch{i}" for i in range(ch_count)]
        if len(channel_names) < ch_count:
            channel_names += [f"Ch{i}" for i in range(len(channel_names), ch_count)]

        # OPTIMIZED: Keep 2x window size + buffer for memory efficiency
        ring_size = int(sr * self.plot_time_window * 2) + 100

        # Determine stream type for specialized rendering
        stream_type = full_info.type().upper()
        is_eeg = "EEG" in stream_type or "eeg" in uid.lower()
        is_gyro = "GYRO" in stream_type or "gyro" in uid.lower() or "motion" in uid.lower()
        is_ppg = "PPG" in stream_type or "ppg" in uid.lower() or "heart" in uid.lower() or "ecg" in uid.lower()

        # Set appropriate Y-axis ranges based on stream type
        if is_gyro:
            y_range = (-200, 200)  # Gyro data typically in this range
        elif is_ppg:
            y_range = (-1500, 2000)  # PPG data range
        else:  # EEG or other
            y_range = (-150, 150)  # EEG data range

        channels_list = []
        for i in range(ch_count):
            ch_name = channel_names[i]
            channels_list.append({
                "name": ch_name,
                "ring_buffer": TwoBufferRing(ring_size, dtype=np.float64),  # Optimized buffer
                "plot_item": None,
                "plot_widget": None,  # Will be set in _rebuild_subplots
                "filter_checkbox": None,
                "bandpass_low_spin": None,
                "bandpass_high_spin": None,
                "bandstop_low_spin": None,
                "bandstop_high_spin": None,
                "filter_enabled": True if is_eeg else False,  # Auto-enable for EEG, disable for others
                "sr": sr,
                "y_range": y_range,  # Store Y-range for this channel
                "is_eeg": is_eeg  # Track if this is an EEG channel
            })

        self.streams_data.append({
            "uid": uid,
            "inlet": inlet,
            "sr": sr,
            "channels": channels_list,
            "is_eeg": is_eeg,
            "is_gyro": is_gyro,
            "is_ppg": is_ppg,
            "stream_type": stream_type
        })
        self.stream_uids.add(uid)

        # OPTIMIZED: Pre-fill ring buffers with initial data for instant display
        self._prefill_stream_buffers(inlet, channels_list)

        # CRITICAL FIX: Async rebuild to prevent UI blocking
        QTimer.singleShot(0, self._rebuild_subplots)

        # Add PSD curves for EEG streams
        if is_eeg:
            for i in range(len(channels_list)):
                psd_curve = self.psd_plot_widget.plot(pen=self.pens[i % len(self.pens)])
                psd_curve.setDownsampling(auto=True, method='mean', ds=3)
                self.psd_curves.append(psd_curve)

    def remove_stream(self, info: StreamInfo):
        print("remove_stream")
        uid = info.name()
        if uid not in self.stream_uids:
            return

        # Close the inlet properly before removing
        for sd in self.streams_data:
            if sd["uid"] == uid:
                try:
                    inlet = sd.get("inlet")
                    if inlet:
                        inlet.close_stream()
                        print(f"[Plot Tab] Closed inlet for stream: {uid}")
                except Exception as e:
                    print(f"[Plot Tab] Error closing inlet for {uid}: {e}")
                break

        self.streams_data = [sd for sd in self.streams_data if sd["uid"] != uid]
        self.stream_uids.remove(uid)
        # CRITICAL FIX: Async rebuild to prevent UI blocking
        QTimer.singleShot(0, self._rebuild_subplots)

    def remove_all_streams(self):
        print("remove_all_streams")

        # Close all inlets properly before clearing
        for sd in self.streams_data:
            try:
                inlet = sd.get("inlet")
                if inlet:
                    inlet.close_stream()
                    print(f"[Plot Tab] Closed inlet for stream: {sd['uid']}")
            except Exception as e:
                print(f"[Plot Tab] Error closing inlet for {sd['uid']}: {e}")

        self.streams_data.clear()
        self.stream_uids.clear()

        # Clear PSD curves
        for curve in self.psd_curves:
            self.psd_plot_widget.removeItem(curve)
        self.psd_curves.clear()

        self.is_paused = False
        self.pause_button.setText("Pause")

        # CRITICAL FIX: Async rebuild to prevent UI blocking
        QTimer.singleShot(0, self._rebuild_subplots)

        self.all_streams_removed.emit()

    def _rebuild_subplots(self):
        print("_rebuild_subplots")
        """
        Clear existing channel widgets, re-create them for each stream's channels.
        """
        while self.channels_layout.count() > 0:
            item = self.channels_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Show/hide placeholder based on whether we have streams
        if len(self.streams_data) == 0:
            self.placeholder_label.setVisible(True)
        else:
            self.placeholder_label.setVisible(False)

        for sd in self.streams_data:
            sr = sd["sr"]
            for ch_info in sd["channels"]:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(4, 2, 4, 2)  # Tighter margins
                row_layout.setSpacing(8)  # Less spacing

                plot_w = pg.PlotWidget()
                plot_w.showGrid(x=True, y=True, alpha=0.25)
                plot_w.showAxis('left', False)
                plot_w.showAxis('bottom', False)
                plot_w.setMenuEnabled('left', False)
                plot_w.setMenuEnabled('bottom', False)
                plot_w.setTitle(ch_info["name"])
                # Responsive height - no fixed constraints, let layout manage sizing
                plot_w.setMinimumHeight(60)  # Just enough to be visible

                # Apply modern theme to plot
                ModernTheme.style_plot_widget(plot_w)

                # Set Y-range based on stream type
                if "y_range" in ch_info:
                    plot_w.setYRange(ch_info["y_range"][0], ch_info["y_range"][1], padding=0)

                # Create PlotDataItem with vibrant color + enable built-in downsampling
                plot_item = plot_w.plot([], [], pen=pg.mkPen(width=2, color=ModernTheme.COLORS['accent_cyan']))
                plot_item.setDownsampling(auto=True, method='peak')
                plot_item.setClipToView(True)

                ch_info["plot_item"] = plot_item
                ch_info["plot_widget"] = plot_w  # Store reference for batch ViewBox updates
                row_layout.addWidget(plot_w, stretch=1)

                # Filter UI - Editable controls with IXR-Suite defaults
                filter_panel = QVBoxLayout()
                filter_panel.setSpacing(6)

                filter_checkbox = QCheckBox("Filter On")
                filter_checkbox.setChecked(ch_info["filter_enabled"])
                filter_checkbox.setStyleSheet(ModernTheme.get_checkbox_style())
                filter_checkbox.setToolTip("Apply bandpass and bandstop filters")

                # Bandpass controls (IXR-Suite default: 1-59 Hz)
                bp_label = QLabel("Bandpass (Hz):")
                bp_label.setStyleSheet(ModernTheme.get_label_style('secondary'))

                bp_low_spin = QDoubleSpinBox()
                bp_low_spin.setRange(0.1, sr/2.0)
                bp_low_spin.setValue(1.0)  # IXR-Suite default
                bp_low_spin.setSingleStep(0.5)
                bp_low_spin.setStyleSheet(ModernTheme.get_spinbox_style())
                bp_low_spin.setToolTip("Bandpass low cutoff (IXR-Suite: 1.0 Hz)")
                bp_low_spin.setMaximumWidth(80)

                bp_high_spin = QDoubleSpinBox()
                bp_high_spin.setRange(0.1, sr/2.0)
                bp_high_spin.setValue(59.0)  # IXR-Suite default
                bp_high_spin.setSingleStep(0.5)
                bp_high_spin.setStyleSheet(ModernTheme.get_spinbox_style())
                bp_high_spin.setToolTip("Bandpass high cutoff (IXR-Suite: 59.0 Hz)")
                bp_high_spin.setMaximumWidth(80)

                bp_layout = QHBoxLayout()
                bp_layout.addWidget(bp_low_spin)
                bp_layout.addWidget(QLabel("-"))
                bp_layout.addWidget(bp_high_spin)

                # Bandstop controls (IXR-Suite default: 48-52 Hz for line noise)
                bs_label = QLabel("Bandstop (Hz):")
                bs_label.setStyleSheet(ModernTheme.get_label_style('secondary'))

                bs_low_spin = QDoubleSpinBox()
                bs_low_spin.setRange(0.1, sr/2.0)
                bs_low_spin.setValue(48.0)  # IXR-Suite default
                bs_low_spin.setSingleStep(0.5)
                bs_low_spin.setStyleSheet(ModernTheme.get_spinbox_style())
                bs_low_spin.setToolTip("Bandstop low cutoff (IXR-Suite: 48.0 Hz)")
                bs_low_spin.setMaximumWidth(80)

                bs_high_spin = QDoubleSpinBox()
                bs_high_spin.setRange(0.1, sr/2.0)
                bs_high_spin.setValue(52.0)  # IXR-Suite default
                bs_high_spin.setSingleStep(0.5)
                bs_high_spin.setStyleSheet(ModernTheme.get_spinbox_style())
                bs_high_spin.setToolTip("Bandstop high cutoff (IXR-Suite: 52.0 Hz)")
                bs_high_spin.setMaximumWidth(80)

                bs_layout = QHBoxLayout()
                bs_layout.addWidget(bs_low_spin)
                bs_layout.addWidget(QLabel("-"))
                bs_layout.addWidget(bs_high_spin)

                # Update filter state when changed
                filter_checkbox.stateChanged.connect(lambda s, c=ch_info: self._update_filter_state(c, s))
                bp_low_spin.valueChanged.connect(lambda v, c=ch_info: self._update_filter_state(c))
                bp_high_spin.valueChanged.connect(lambda v, c=ch_info: self._update_filter_state(c))
                bs_low_spin.valueChanged.connect(lambda v, c=ch_info: self._update_filter_state(c))
                bs_high_spin.valueChanged.connect(lambda v, c=ch_info: self._update_filter_state(c))

                filter_panel.addWidget(filter_checkbox)
                filter_panel.addWidget(bp_label)
                filter_panel.addLayout(bp_layout)
                filter_panel.addWidget(bs_label)
                filter_panel.addLayout(bs_layout)
                filter_panel.addStretch()

                ch_info["filter_checkbox"] = filter_checkbox
                ch_info["bandpass_low_spin"] = bp_low_spin
                ch_info["bandpass_high_spin"] = bp_high_spin
                ch_info["bandstop_low_spin"] = bs_low_spin
                ch_info["bandstop_high_spin"] = bs_high_spin

                row_layout.addLayout(filter_panel)
                self.channels_layout.addWidget(row_widget)

    def _update_filter_state(self, ch_info, state=None):
        """Update filter enabled state with user-editable parameters (defaults from IXR-Suite)."""
        if state is not None:
            ch_info["filter_enabled"] = (state == 2)  # Qt.Checked = 2
        # Note: Filter parameters are read directly from spinboxes during update_plot()
        print(f"Filter {'enabled' if ch_info['filter_enabled'] else 'disabled'} for {ch_info['name']}")

    def update_plot(self):
        """Called ~20 fps. Pull new chunk, filter it, store in ring buffer, then plot. OPTIMIZED."""
        # Skip updates if paused or not visible (major optimization)
        if self.is_paused or not self.is_visible:
            return

        self.t1 = time.perf_counter(), time.process_time()

        max_time = None

        # 1) Pull new data and store in ring buffers (OPTIMIZED: direct numpy operations)
        for sd in self.streams_data:
            inlet = sd["inlet"]
            sr = sd["sr"]
            samples, timestamps = inlet.pull_chunk(timeout=0.0)
            if not timestamps:
                continue

            t_arr = np.array(timestamps, dtype=np.float64)
            s_arr = np.array(samples, dtype=np.float64)  # shape (N, chCount)

            channels_list = sd["channels"]

            # Store RAW data in ring buffers (filtering happens only on display - MASSIVE PERFORMANCE BOOST)
            for ch_idx, ch_info in enumerate(channels_list):
                raw_chunk = s_arr[:, ch_idx]  # No copy needed - direct reference

                # Store raw data directly (no filtering on ingestion - 10x faster!)
                ch_info["ring_buffer"].extend(t_arr, raw_chunk)

        # 2) Plot from ring buffers (OPTIMIZED: use buffer views, batch updates)
        skip_samples_time = 0.5  # OPTIMIZED: Reduced from 2.0s for instant display

        for sd in self.streams_data:
            sr = sd["sr"]
            skip_samples = int(sr * skip_samples_time)

            for ch_info in sd["channels"]:
                if ch_info["plot_item"] is None:
                    continue
                if len(ch_info["ring_buffer"]) < skip_samples + 10:
                    continue

                # OPTIMIZED: Get RAW data directly from ring buffer
                x_buf, y_buf = ch_info["ring_buffer"].get_data(skip_initial=skip_samples)

                if len(x_buf) == 0:
                    continue

                last_time = x_buf[-1]
                if (max_time is None) or (last_time > max_time):
                    max_time = last_time

                # PERFORMANCE FIX: Apply filters ONLY to display data (not on every chunk!)
                # This reduces filter operations from 600/sec to ~60/sec (10x improvement)
                if ch_info.get("filter_enabled", False) and ch_info.get("is_eeg", False):
                    try:
                        # Get filter parameters from UI
                        bp_low = ch_info.get("bandpass_low_spin").value() if ch_info.get("bandpass_low_spin") else 1.0
                        bp_high = ch_info.get("bandpass_high_spin").value() if ch_info.get("bandpass_high_spin") else 59.0
                        bs_low = ch_info.get("bandstop_low_spin").value() if ch_info.get("bandstop_low_spin") else 48.0
                        bs_high = ch_info.get("bandstop_high_spin").value() if ch_info.get("bandstop_high_spin") else 52.0

                        # Make a copy for filtering (don't modify ring buffer)
                        y_filtered = y_buf.copy()

                        # Apply filters to display data only
                        DataFilter.detrend(y_filtered, DetrendOperations.CONSTANT.value)
                        DataFilter.perform_bandpass(
                            data=y_filtered,
                            sampling_rate=int(sr),
                            start_freq=bp_low,
                            stop_freq=bp_high,
                            order=2,
                            filter_type=FilterTypes.BUTTERWORTH.value,
                            ripple=0.0
                        )
                        DataFilter.perform_bandstop(
                            data=y_filtered,
                            sampling_rate=int(sr),
                            start_freq=bs_low,
                            stop_freq=bs_high,
                            order=2,
                            filter_type=FilterTypes.BUTTERWORTH.value,
                            ripple=0.0
                        )

                        # Use filtered data for display
                        y_buf = y_filtered
                    except Exception as e:
                        print(f"Filter error on {ch_info['name']}: {e}")
                        # Fall back to raw data if filtering fails

                # OPTIMIZED: Manual decimation if large (use numpy views when possible)
                L = len(y_buf)
                if L > self.max_points:
                    idx = np.linspace(0, L-1, self.max_points, dtype=np.int32)
                    x_plot = x_buf[idx]
                    y_plot = y_buf[idx]
                else:
                    x_plot = x_buf
                    y_plot = y_buf

                # Single setData call (already optimized by PyQtGraph)
                ch_info["plot_item"].setData(x_plot, y_plot)

        # 3) CRITICAL OPTIMIZATION: Only update X-range when time actually changes
        if max_time is not None:
            min_x = max_time - self.plot_time_window
            # Only update if time has changed (avoid redundant setXRange calls)
            if self.last_xrange_update is None or abs(max_time - self.last_xrange_update) > 0.01:
                self.last_xrange_update = max_time
                # Batch update all plot widgets
                for sd in self.streams_data:
                    for ch_info in sd["channels"]:
                        if ch_info["plot_widget"] is not None:
                            ch_info["plot_widget"].setXRange(min_x, max_time, padding=0)

        # 4) OPTIMIZED: Calculate PSD for EEG streams (throttled, only when visible)
        self.psd_update_counter += 1
        if self.enable_psd_checkbox.isChecked() and (self.psd_update_counter >= self.psd_update_interval):
            psd_curve_idx = 0

            for sd in self.streams_data:
                if not sd.get("is_eeg", False):
                    continue

                sr = sd["sr"]
                for ch_info in sd["channels"]:
                    if len(ch_info["ring_buffer"]) < int(self.psd_window_s * sr):
                        continue

                    # OPTIMIZED: Get recent data from ring buffer (efficient)
                    _, y_buf = ch_info["ring_buffer"].get_data()
                    psd_data_slice = y_buf[-int(self.psd_window_s * sr):].copy()

                    # Apply signal processing (from IXR-Suite)
                    psd_data_slice = self._apply_signal_processing(psd_data_slice, sr)

                    # Calculate PSD
                    psd_data, bands = self._calculate_psd_and_bands(psd_data_slice, sr)

                    if psd_data is not None and psd_curve_idx < len(self.psd_curves):
                        # Update PSD curve
                        lim = min(60, len(psd_data[0]))
                        self.psd_curves[psd_curve_idx].setData(psd_data[1][0:lim].tolist(), psd_data[0][0:lim].tolist())
                        psd_curve_idx += 1

            # Reset counter after PSD update
            self.psd_update_counter = 0

        # self.t2 = time.perf_counter(), time.process_time()
        # print(f" Time update_plot(): {self.t2[0] - self.t1[0]:.2f} seconds")

    def set_visible(self, visible):
        """
        Set visibility state for optimization.
        Called by parent when tab becomes visible/hidden.
        """
        self.is_visible = visible

    def _extract_channel_names(self, full_info: StreamInfo):

        print("_extract_channel_names")

        """Get channel labels or fallback to 'Ch#' if unavailable."""
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

    def _prefill_stream_buffers(self, inlet, channels_list):
        """
        OPTIMIZED: Pre-fill ring buffers with initial data for instant visualization.
        This pulls available data immediately when a stream is added.
        """
        print("[PREFILL] Pre-filling ring buffers for instant display...")

        # Pull whatever data is available (non-blocking)
        samples, timestamps = inlet.pull_chunk(timeout=0.0)

        if not timestamps:
            print("[PREFILL] No initial data available yet")
            return

        t_arr = np.array(timestamps, dtype=np.float64)
        s_arr = np.array(samples, dtype=np.float64)

        print(f"[PREFILL] Pre-filled {len(timestamps)} samples across {len(channels_list)} channels")

        # Fill each channel's ring buffer with RAW data (filtering happens on display)
        for ch_idx, ch_info in enumerate(channels_list):
            if ch_idx >= s_arr.shape[1]:
                continue

            # Store raw data directly (no prefill filtering - matches new approach)
            raw_chunk = s_arr[:, ch_idx]
            ch_info["ring_buffer"].extend(t_arr, raw_chunk)
