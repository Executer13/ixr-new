# lsl_browser_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMenu
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QBrush, QColor
from pylsl import StreamInfo
from sensors.lsl_fetcher import LSLFetcher

class LSLBrowserWidget(QWidget):
    add_stream_requested = pyqtSignal(StreamInfo)
    remove_stream_requested = pyqtSignal(StreamInfo)

    def __init__(self, lsl_fetcher: LSLFetcher, parent=None):
        super().__init__(parent)
        self.lsl_fetcher = lsl_fetcher
        self.init_ui()
        self.streams_in_plot = set()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.refresh_button = QPushButton("Refresh Streams")
        self.refresh_button.clicked.connect(self.refresh_streams)
        layout.addWidget(self.refresh_button)

        self.stream_list = QListWidget()
        self.stream_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stream_list.customContextMenuRequested.connect(self.open_context_menu)
        self.stream_list.itemDoubleClicked.connect(self.handle_item_double_click)
        layout.addWidget(self.stream_list)

        self.setLayout(layout)

    def refresh_streams(self):
        self.stream_list.clear()
        streams = self.lsl_fetcher.get_available_streams()
        for s in streams:
            hostname_part = s.hostname() or "UnknownHost"
            name_part = s.name() or "noname"
            type_part = s.type() or "notype"
            uid_part = s.uid() or "nouid"
            src_part = s.source_id() or "nosrc"
            ch_part = str(s.channel_count())
            unique_id = f"[{hostname_part}] {name_part}-{type_part}-{ch_part}-{uid_part}-{src_part}"

            item_text = f"[{hostname_part}] {s.name()} ({s.type()}) - {s.channel_count()} ch"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, s)
            item.setData(Qt.UserRole + 1, unique_id)
            # Store original text in UserRole+2 so we can revert later
            item.setData(Qt.UserRole + 2, item_text)

            if unique_id in self.streams_in_plot:
                self._set_item_highlighted(item, True)
            self.stream_list.addItem(item)

    def handle_item_double_click(self, item):
        if not item:
            return
        stream_info = item.data(Qt.UserRole)
        unique_id = item.data(Qt.UserRole + 1)

        if unique_id in self.streams_in_plot:
            self.remove_stream_requested.emit(stream_info)
            self.streams_in_plot.remove(unique_id)
            self._set_item_highlighted(item, False)
        else:
            self.add_stream_requested.emit(stream_info)
            self.streams_in_plot.add(unique_id)
            self._set_item_highlighted(item, True)

    def open_context_menu(self, pos: QPoint):
        item = self.stream_list.itemAt(pos)
        if not item:
            return
        
        stream_info = item.data(Qt.UserRole)
        unique_id = item.data(Qt.UserRole + 1)

        menu = QMenu(self)
        if unique_id in self.streams_in_plot:
            remove_action = menu.addAction("Remove from Plot")
            chosen_action = menu.exec_(self.stream_list.mapToGlobal(pos))
            if chosen_action == remove_action:
                self.remove_stream_requested.emit(stream_info)
                self.streams_in_plot.remove(unique_id)
                self._set_item_highlighted(item, False)
        else:
            add_action = menu.addAction("Add to Plot")
            chosen_action = menu.exec_(self.stream_list.mapToGlobal(pos))
            if chosen_action == add_action:
                self.add_stream_requested.emit(stream_info)
                self.streams_in_plot.add(unique_id)
                self._set_item_highlighted(item, True)

    def _set_item_highlighted(self, item, highlighted):
        """
        Changes background color and appends '[Plotting]' to the right
        if currently being plotted.
        """
        orig_text = item.data(Qt.UserRole + 2)
        if highlighted:
            # Approximate right flush by using whitespace, then append.
            # Adjust spacing to your preference.
            new_text = f"{orig_text:<60} [Plotting]"
            item.setText(new_text)
            item.setBackground(QBrush(QColor(200, 255, 200)))  # light green
        else:
            # Restore original text
            item.setText(orig_text)
            item.setBackground(QBrush(Qt.white))

    def clear_all_plot_markers(self):
        """
        Clears the streams_in_plot set and removes any green highlighting
        plus the '[Plotting]' suffix from all items.
        """
        self.streams_in_plot.clear()
        for i in range(self.stream_list.count()):
            item = self.stream_list.item(i)
            if item:
                self._set_item_highlighted(item, False)