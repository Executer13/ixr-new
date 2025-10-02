# sensor_interface.py

from PyQt5.QtCore import QObject, pyqtSignal
import threading
import time

class SensorInterface(QObject):
    # Signal emitted when sensor status changes (e.g., "Connected", "Disconnected", etc.)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super(SensorInterface, self).__init__()
        self.connected = False
        self._status_running = False
        self._status_thread = None
        self._last_status = None
        # Auto-reconnect settings
        self.auto_reconnect_enabled = True
        self.reconnect_interval = 2  # seconds between reconnect attempts
        self._last_reconnect_attempt = 0

    def connect(self):
        """Establish connection to the sensor.
           Subclasses should override this with sensor-specific connection logic.
        """
        # Placeholder connection logic (subclasses override this)
        self.connected = True
        print("Sensor connected.")
        self.start_status_check()

    def start_stream(self):
        """Begin streaming sensor data."""
        if not self.connected:
            raise Exception("Sensor not connected.")
        print("Sensor stream started.")

    def stop_stream(self):
        """Stop streaming sensor data."""
        if not self.connected:
            raise Exception("Sensor not connected.")
        print("Sensor stream stopped.")

    def disconnect(self):
        """Disconnect the sensor.
           Subclasses should override this with sensor-specific disconnection logic.
        """
        self.connected = False
        print("Sensor disconnected.")
        self.stop_status_check()

    def get_status(self):
        """
        Return a string representing the sensor's current status.
        Subclasses can override this method to provide more detailed status.
        """
        return "Connected" if self.connected else "Disconnected"

    def _status_worker(self):
        """
        Background thread that checks the sensor's status periodically.
        If the status changes, it emits the status_changed signal.
        Also, if auto-reconnect is enabled and the sensor is disconnected,
        it attempts to reconnect after a defined interval.
        """
        while self._status_running:
            current_status = self.get_status()
            if current_status != self._last_status:
                self._last_status = current_status
                self.status_changed.emit(current_status)
            # If auto-reconnect is enabled and sensor is disconnected,
            # attempt to reconnect at defined intervals.
            if self.auto_reconnect_enabled and current_status == "Not Alive":
                now = time.time()
                if now - self._last_reconnect_attempt >= self.reconnect_interval:
                    self._last_reconnect_attempt = now
                    print("Auto-reconnect: attempting to reconnect sensor.")
                    self.connect()  # Expected to be non-blocking (or spawn its own thread)
            time.sleep(1)

    def start_status_check(self):
        """Starts the background thread for status monitoring."""
        if not self._status_running:
            self._status_running = True
            self._status_thread = threading.Thread(target=self._status_worker, daemon=True)
            self._status_thread.start()

    def stop_status_check(self):
        """Stops the background status-checking thread."""
        self._status_running = False
        if self._status_thread:
            self._status_thread.join(timeout=2)
