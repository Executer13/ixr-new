# plot_tab.py

import numpy as np
import pyqtgraph as pg
pg.setConfigOptions(useOpenGL=True)
from collections import deque
from scipy.signal import iirfilter, lfilter, lfilter_zi
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QCheckBox,
    QScrollArea
)
from pylsl import StreamInlet, StreamInfo
import time

class PlotTab(QWidget):
    """
    A tab that plots multiple LSL streams via PyQtGraph, using ring buffers
    but only filtering newly arrived chunks, plus manual downsampling.
    """

    all_streams_removed = pyqtSignal()  # Emitted when "Remove All Streams" is pressed

    def __init__(self, parent=None):
        print("__init__")
        super().__init__(parent)

        self.t1 = time.perf_counter(), time.process_time()
        self.t2 = time.perf_counter(), time.process_time()
        self.t3 = time.perf_counter(), time.process_time()
        self.t4 = time.perf_counter(), time.process_time()

        self.plot_time_window = 10.0    # default time window in seconds
        self.refresh_rate = 20.0       # ~20 fps
        self.max_points = 2000         # manual decimation limit

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Control bar (pause, remove streams, time window)
        control_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.remove_button = QPushButton("Remove All Streams")
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.remove_button)

        self.window_label = QLabel("Window (s):")
        self.window_spin = QDoubleSpinBox()
        self.window_spin.setRange(0.1, 60.0)
        self.window_spin.setValue(self.plot_time_window)
        self.window_spin.setSingleStep(0.5)

        control_layout.addWidget(self.window_label)
        control_layout.addWidget(self.window_spin)
        self.main_layout.addLayout(control_layout)

        # Scroll area for channel rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        # Container & layout for channels
        self.channels_container = QWidget()
        self.channels_layout = QVBoxLayout(self.channels_container)
        self.channels_container.setLayout(self.channels_layout)
        self.scroll_area.setWidget(self.channels_container)

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
        # Each channel dict:
        # {
        #   "name": str,
        #   "x_deque": deque,    # times (filtered chunk appended)
        #   "y_deque": deque,    # filtered data appended
        #   "plot_item": PlotDataItem,
        #   "filter_checkbox": QCheckBox,
        #   "cutoff_spin": QDoubleSpinBox,
        #   "filter_ba": (b,a),
        #   "filter_zi": np.array,
        #   "sr": float
        # }

        self.streams_data = []
        self.stream_uids = set()
        self.is_paused = True

        # Wire up signals
        self.pause_button.clicked.connect(self.toggle_pause)
        self.remove_button.clicked.connect(self.remove_all_streams)
        self.window_spin.valueChanged.connect(self.on_window_spin_changed)

        # Timer for pulling data & updating
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / self.refresh_rate))  # ~20 fps

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

    def add_stream(self, info: StreamInfo):
        print("add_stream")
        """
        Add a new stream if not already present. 
        Create an inlet, parse channel info, store them in self.streams_data,
        then rebuild the subplots.
        """
        uid = info.name()
        if uid in self.stream_uids:
            return

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

        ring_size = int(sr * self.plot_time_window) + 50

        channels_list = []
        for i in range(ch_count):
            ch_name = channel_names[i]
            channels_list.append({
                "name": ch_name,
                "x_deque": deque(maxlen=ring_size),
                "y_deque": deque(maxlen=ring_size),
                "plot_item": None,
                "filter_checkbox": None,
                "cutoff_spin": None,
                "filter_ba": None,
                "filter_zi": None,
                "sr": sr
            })

        self.streams_data.append({
            "uid": uid,
            "inlet": inlet,
            "sr": sr,
            "channels": channels_list
        })
        self.stream_uids.add(uid)
        self._rebuild_subplots()

    def remove_stream(self, info: StreamInfo):
        print("remove_stream")
        uid = info.name()
        if uid not in self.stream_uids:
            return
        self.streams_data = [sd for sd in self.streams_data if sd["uid"] != uid]
        self.stream_uids.remove(uid)
        self._rebuild_subplots()

    def remove_all_streams(self):
        print("remove_all_streams")
        self.streams_data.clear()
        self.stream_uids.clear()
        self._rebuild_subplots()

        self.is_paused = False
        self.pause_button.setText("Pause")

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

        for sd in self.streams_data:
            sr = sd["sr"]
            for ch_info in sd["channels"]:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0,0,0,0)

                plot_w = pg.PlotWidget()
                plot_w.showGrid(x=False, y=False)
                plot_w.showAxis('left', False)
                plot_w.showAxis('bottom', False)
                plot_w.setMenuEnabled('left', False)
                plot_w.setMenuEnabled('bottom', False)
                plot_w.setTitle(ch_info["name"])

                # Create PlotDataItem + enable built-in downsampling
                plot_item = plot_w.plot([], [], pen=pg.mkPen(width=1.5))
                plot_item.setDownsampling(auto=True, method='peak')
                plot_item.setClipToView(True)

                ch_info["plot_item"] = plot_item
                row_layout.addWidget(plot_w, stretch=1)

                # Filter UI
                filter_panel = QVBoxLayout()
                filter_checkbox = QCheckBox("Filter On")
                filter_checkbox.setChecked(True)
                cutoff_spin = QDoubleSpinBox()
                cutoff_spin.setRange(1.0, sr/2.0)
                cutoff_spin.setValue(40.0)
                cutoff_spin.setSingleStep(1.0)

                # re-init filter coeffs when toggled or changed
                filter_checkbox.stateChanged.connect(lambda s, c=ch_info: self._update_filter_coeffs(c))
                cutoff_spin.valueChanged.connect(lambda v, c=ch_info: self._update_filter_coeffs(c))

                filter_panel.addWidget(filter_checkbox)
                filter_panel.addWidget(QLabel("Cut-off (Hz):"))
                filter_panel.addWidget(cutoff_spin)
                filter_panel.addStretch()

                ch_info["filter_checkbox"] = filter_checkbox
                ch_info["cutoff_spin"] = cutoff_spin

                self._update_filter_coeffs(ch_info)

                row_layout.addLayout(filter_panel)
                self.channels_layout.addWidget(row_widget)

    def _update_filter_coeffs(self, ch_info):
        
        print("_update_filter_coeffs")

        """Compute streaming IIR filter if user wants it. 4th-order lowpass (cutoff <= sr/2)."""
        if not ch_info["filter_checkbox"].isChecked():
            ch_info["filter_ba"] = None
            ch_info["filter_zi"] = None
            return

        sr = ch_info["sr"]
        cutoff = ch_info["cutoff_spin"].value()
        if cutoff >= sr/2.0:
            ch_info["filter_ba"] = None
            ch_info["filter_zi"] = None
            return

        b, a = iirfilter(
            N=4,
            Wn=(cutoff / (sr/2.0)),
            btype='low',
            analog=False,
            ftype='butter'
        )
        ch_info["filter_ba"] = (b,a)
        ch_info["filter_zi"] = lfilter_zi(b,a)*0.0

    def update_plot(self):
        """Called ~20 fps. Pull new chunk, filter it, store in ring buffer, then plot."""
        if self.is_paused:
            return

        self.t1 = time.perf_counter(), time.process_time()
        # print(f" Time between update_plot(): {self.t1[0] - self.t2[0]:.2f} seconds")
        
        max_time = None

        # 1) Pull new data
        for sd in self.streams_data:
            inlet = sd["inlet"]
            sr = sd["sr"]
            samples, timestamps = inlet.pull_chunk(timeout=0.0)
            if not timestamps:
                continue

            t_arr = np.array(timestamps, dtype=float)
            s_arr = np.array(samples, dtype=float)  # shape (N, chCount)
            N = len(t_arr)

            channels_list = sd["channels"]

            # For each channel, apply streaming filter to new chunk
            for ch_idx, ch_info in enumerate(channels_list):
                raw_chunk = s_arr[:, ch_idx]
                if ch_info["filter_ba"] is not None:
                    b, a = ch_info["filter_ba"]
                    zi = ch_info["filter_zi"]
                    filt_chunk, zi = lfilter(b, a, raw_chunk, zi=zi)
                    ch_info["filter_zi"] = zi
                    chunk_data = filt_chunk
                else:
                    chunk_data = raw_chunk

                # Append the filtered chunk to ring buffer
                for i in range(N):
                    ch_info["x_deque"].append(t_arr[i])
                    ch_info["y_deque"].append(chunk_data[i])

        # 2) Plot from ring buffers
        for sd in self.streams_data:
            for ch_info in sd["channels"]:
                if ch_info["plot_item"] is None:
                    continue  # subplot not built yet
                if len(ch_info["x_deque"]) < 1:
                    continue

                x_buf = np.array(ch_info["x_deque"], dtype=float)
                y_buf = np.array(ch_info["y_deque"], dtype=float)

                last_time = x_buf[-1]
                if (max_time is None) or (last_time > max_time):
                    max_time = last_time

                # Zero-center & scale
                mean_val = y_buf.mean()
                centered = y_buf - mean_val
                std_val = centered.std()
                if std_val < 1e-12:
                    std_val = 1.0
                scaled = centered / std_val

                # Manual decimation if large
                L = len(scaled)
                if L > self.max_points:
                    idx = np.linspace(0, L-1, self.max_points).astype(int)
                    x_plot = x_buf[idx]
                    y_plot = scaled[idx]
                else:
                    x_plot = x_buf
                    y_plot = scaled

                ch_info["plot_item"].setData(x_plot, y_plot)
                ch_info["plot_item"].setData(x_buf, scaled)

        # 3) Auto-scroll
        if max_time is not None:
            min_x = max_time - self.plot_time_window
            for sd in self.streams_data:
                for ch_info in sd["channels"]:
                    if ch_info["plot_item"] is not None:
                        vb = ch_info["plot_item"].getViewBox()
                        if vb is not None:
                            vb.setXRange(min_x, max_time)

        # self.t2 = time.perf_counter(), time.process_time()
        # print(f" Time update_plot(): {self.t2[0] - self.t1[0]:.2f} seconds")

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
