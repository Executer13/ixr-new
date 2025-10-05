# lsl_browser_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMenu
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QBrush, QColor, QIcon
from pylsl import StreamInfo
from src.infrastructure.streaming.lsl_fetcher import LSLFetcher
from gui.modern_theme import ModernTheme

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Modern refresh button with icon and success (green) styling
        self.refresh_button = QPushButton("  Refresh Streams")
        self.refresh_button.setStyleSheet(ModernTheme.get_button_style('success'))

        # Add refresh icon using Unicode symbol
        refresh_icon = "↻"  # Unicode refresh symbol
        self.refresh_button.setText(f"{refresh_icon}  Refresh Streams")

        self.refresh_button.clicked.connect(self.refresh_streams)
        layout.addWidget(self.refresh_button)

        # Modern list widget styling
        self.stream_list = QListWidget()
        self.stream_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stream_list.customContextMenuRequested.connect(self.open_context_menu)
        self.stream_list.itemDoubleClicked.connect(self.handle_item_double_click)
        self.stream_list.setStyleSheet(f"""
            QListWidget {{
                background: {ModernTheme.COLORS['bg_primary']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 8px;
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-radius: 6px;
                margin: 2px 0px;
            }}
            QListWidget::item:hover {{
                background: {ModernTheme.COLORS['bg_secondary']};
            }}
            QListWidget::item:selected {{
                background: {ModernTheme.COLORS['bg_secondary']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self.stream_list)

        self.setLayout(layout)

    def refresh_streams(self):
        self.stream_list.clear()
        streams = self.lsl_fetcher.get_available_streams()
        self._populate_stream_list(streams)

    def async_refresh_streams(self):
        """
        Asynchronously refresh streams (non-blocking).
        Uses LSLFetcher's async discovery.
        """
        print("[LSL Browser] Starting async stream refresh...")
        self.lsl_fetcher.get_available_streams_async(
            callback=self._on_async_streams_discovered,
            wait_time=0.1  # OPTIMIZED: Minimal wait for instant discovery
        )

    def _on_async_streams_discovered(self, streams):
        """Callback when async stream discovery completes."""
        print(f"[LSL Browser] Async discovery complete: {len(streams)} streams found")
        self.stream_list.clear()
        self._populate_stream_list(streams)

    def _populate_stream_list(self, streams):
        """Populate the stream list with discovered streams."""
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
        menu.setStyleSheet(f"""
            QMenu {{
                background: {ModernTheme.COLORS['card_bg']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 8px;
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background: {ModernTheme.COLORS['bg_secondary']};
            }}
        """)
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
        if currently being plotted - using modern theme colors.
        """
        orig_text = item.data(Qt.UserRole + 2)
        if highlighted:
            # Approximate right flush by using whitespace, then append.
            new_text = f"{orig_text:<60} [Plotting]"
            item.setText(new_text)
            # Use modern theme success color with transparency
            highlight_color = QColor(ModernTheme.COLORS['success'])
            highlight_color.setAlpha(40)  # Subtle highlight
            item.setBackground(QBrush(highlight_color))
            item.setForeground(QBrush(QColor(ModernTheme.COLORS['text_primary'])))
        else:
            # Restore original text
            item.setText(orig_text)
            item.setBackground(QBrush(QColor('transparent')))
            item.setForeground(QBrush(QColor(ModernTheme.COLORS['text_primary'])))

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