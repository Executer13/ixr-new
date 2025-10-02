import time
from PyQt5.QtCore import pyqtSignal
from sensors.sensor_interface import SensorInterface

from bleak import BleakScanner, BleakClient
from pylsl import StreamInfo, StreamOutlet, local_clock
import pylsl

from sensors.ble_event_loop import BleEventLoop  # Adjust path if needed

# Polar-specific constants
MODEL_NBR_UUID         = "00002a24-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID     = "00002a19-0000-1000-8000-00805f9b34fb"
PMD_CONTROL            = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_DATA               = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"
ECG_WRITE              = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
ECG_SAMPLING_FREQ      = 130


class PolarSensor(SensorInterface):
    """
    A SensorInterface subclass that scans for a Polar H10 belt via BLE,
    connects, and streams ECG data to LSL at ~130 Hz.
    Now uses a single persistent event loop from ble_event_loop.py 
    to avoid 'Event loop is closed' issues.
    """

    def __init__(self):
        super().__init__()
        self.ble_client = None
        self.outlet = None
        self.auto_reconnect_enabled = True

        # For displaying a 'first sample arrived' message
        self._first_ecg_sample_received = False

    def connect(self):
        """
        Non-blocking connect: we schedule an async coroutine on the single BLE event loop.
        """
        self.status_changed.emit("Scanning for Polar devices...")
        BleEventLoop.instance().run_in_loop(self._async_connect())

    async def _async_connect(self):
        """
        Actual scanning + connecting on the shared event loop.
        """
        try:
            devices = await BleakScanner.discover()
            polar_dev = next((d for d in devices if d.name and "Polar" in d.name), None)
            if not polar_dev:
                raise Exception("No Polar device found.")

            self.ble_client = BleakClient(polar_dev.address)
            await self.ble_client.connect()

            if not self.ble_client.is_connected:
                raise Exception("BleakClient could not connect to Polar H10.")

            # Read battery
            battery_data = await self.ble_client.read_gatt_char(BATTERY_LEVEL_UUID)
            battery_level = int(battery_data[0]) if battery_data else -1
            self.status_changed.emit(f"Polar H10 battery level: {battery_level}%")

            self.connected = True
            self.status_changed.emit("Connected")
            self.start_status_check()
            self.start_stream()

        except Exception as e:
            self.connected = False
            self.status_changed.emit(f"Connection failed: {str(e)}")

    def start_stream(self):
        if not self.connected or not self.ble_client:
            raise Exception("PolarSensor not connected.")

        if not self.outlet:
            info = StreamInfo("PolarBand", "ECG", 1, ECG_SAMPLING_FREQ, 'float32', 'myuid2424')
            info.desc().append_child_value("manufacturer", "Polar")
            channels = info.desc().append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("name", "ECG")
            ch.append_child_value("unit", "microvolts")
            ch.append_child_value("type", "ECG")
            self.outlet = StreamOutlet(info)
            self.status_changed.emit("LSL stream created. Data may take a few seconds to appear...")

        # reset the 'first sample' flag
        self._first_ecg_sample_received = False

        # Start notifications on the event loop
        BleEventLoop.instance().run_in_loop(self._start_notify_task())

    async def _start_notify_task(self):
        try:
            await self.ble_client.write_gatt_char(PMD_CONTROL, ECG_WRITE)
            await self.ble_client.start_notify(PMD_DATA, self._notification_handler)
        except Exception as e:
            self.status_changed.emit(f"PolarSensor: Failed to start notify: {str(e)}")

    def stop_stream(self):
        if not self.connected or not self.ble_client:
            return
        BleEventLoop.instance().run_in_loop(self._stop_notify_task())

    async def _stop_notify_task(self):
        try:
            await self.ble_client.stop_notify(PMD_DATA)
            self.status_changed.emit("LSL stream stopped")
        except Exception as e:
            self.status_changed.emit(f"PolarSensor: Failed to stop notify: {str(e)}")

    def disconnect(self):
        """
        Disconnect from Polar, disable auto-reconnect, stop status checks, etc.
        """
        self.auto_reconnect_enabled = False
        self.stop_status_check()
        BleEventLoop.instance().run_in_loop(self._async_disconnect())

    async def _async_disconnect(self):
        try:
            if self.ble_client and self.ble_client.is_connected:
                await self.ble_client.disconnect()
            self.connected = False
            self.ble_client = None
            self.outlet = None
            self.status_changed.emit("Disconnected")
        except Exception as e:
            self.status_changed.emit(f"PolarSensor: Disconnect error: {str(e)}")

    def get_status(self):
        if not self.connected and not self.auto_reconnect_enabled:
            return "Disconnected"
        elif self.connected:
            return "Alive"
        else:
            return "Not Alive. Attempting automatic reconnection."

    def _notification_handler(self, sender: str, data: bytearray):
        """
        Called by Bleak when new ECG data arrives.
        """
        if not self.outlet:
            return
        if data and data[0] == 0x00:
            step = 3
            samples = data[10:]
            offset = 0
            ecg_values = []
            while offset < len(samples):
                val = int.from_bytes(samples[offset:offset+step], byteorder="little", signed=True)
                ecg_values.append(val)
                offset += step

            if not self._first_ecg_sample_received and len(ecg_values) > 0:
                self._first_ecg_sample_received = True
                self.status_changed.emit("Polar ECG data is now arriving!")

            stamp = local_clock()
            self.outlet.push_chunk(ecg_values, stamp)

    def _status_worker(self):
        while self._status_running:
            current_status = self.get_status()
            if current_status != self._last_status:
                self._last_status = current_status
                self.status_changed.emit(current_status)

            if self.auto_reconnect_enabled and current_status.startswith("Not Alive"):
                now = time.time()
                if now - self._last_reconnect_attempt >= self.reconnect_interval:
                    self._last_reconnect_attempt = now
                    self.stop_stream()
                    time.sleep(1)
                    self.connect()

            time.sleep(10)
