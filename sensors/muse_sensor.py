# muse_sensor.py

import threading
from threading import Event
import time
from sensors.sensor_interface import SensorInterface
from sensors.brainflow_handler import BrainFlowHandler
from sensors.brainflow_lsl_publisher import BrainFlowLSLPublisher
from brainflow.board_shim import BrainFlowInputParams, BoardIds, BoardShim

class MuseSensor(SensorInterface):
    def __init__(self):
        super(MuseSensor, self).__init__()
        self.board_id = BoardIds.MUSE_S_BOARD.value
        self.input_params = BrainFlowInputParams()
        self.handler = None
        self.auto_reconnect_enabled = True

    def connect(self):
        self.auto_reconnect_enabled = True
        def connect_worker():
            try:
                self.handler = BrainFlowHandler(self.board_id, self.input_params)
                self.handler.prepare_and_connect_board()
                time.sleep(2.0)  # Allow some time for the handler to update its status
                if self.handler.is_alive():
                    self.connected = True
                    self.status_changed.emit("Connected")
                    print("MuseSensor: Connected via BrainFlowHandler.")
                    self.start_status_check()
                    self.start_stream()
                else:
                    self.connected = False
                    error_message = "Connection failed: Board not ready"
                    self.status_changed.emit(error_message)
                    print("MuseSensor:", error_message)
            except Exception as e:
                self.connected = False
                error_message = f"Connection failed: {str(e)}"
                self.status_changed.emit(error_message)
                print("MuseSensor: Connection failed:", e)
        threading.Thread(target=connect_worker, daemon=True).start()

    def disconnect(self):
        # Disable auto-reconnect to prevent immediate reconnection.
        self.auto_reconnect_enabled = False
        self.stop_status_check()
        def disconnect_worker():
            try:
                if self.handler:
                    self.stop_stream()
                    time.sleep(1.0)  # Allow time for the stream to stop
                    self.handler.delete_board()
                    # Fully clean up lingering sessions:
                    BoardShim.release_all_sessions()
                    print("MuseSensor: Disconnected successfully.")
                    self.status_changed.emit("Disconnected")
                    self._last_status = "Disconnected"
            except Exception as e:
                error_message = f"Error during disconnect: {str(e)}"
                self.status_changed.emit(error_message)
                print("MuseSensor: Error during disconnect:", e)
            finally:
                self.connected = False
                self.handler = None
            # Optionally, wait a few seconds to ensure complete cleanup before allowing reconnection.
            time.sleep(2.0)
        threading.Thread(target=disconnect_worker, daemon=True).start()

    def start_stream(self):
        if not self.connected:
            raise Exception("MuseSensor not connected.")
        # If no publisher exists, create one; otherwise, update its board and resume streaming.
        if not hasattr(self, 'lsl_publisher') or self.lsl_publisher is None:
            
            self._lsl_stay_alive = Event()
            self._lsl_stay_alive.set()
            self._lsl_streaming_enabled = Event()
            self._lsl_streaming_enabled.set()

            self.lsl_publisher = BrainFlowLSLPublisher(
                board_shim=self.handler.board,
                stay_alive=self._lsl_stay_alive,
                streaming_enabled=self._lsl_streaming_enabled
            )
            self.lsl_publisher.start()
            print("LSL stream started.")
            self.status_changed.emit("LSL stream started")
        else:
            # Update the publisher's board with the current board from the handler.
            self.lsl_publisher.update_board(self.handler.board)
            # Resume streaming by ensuring the do_stream and streaming_enabled events are set.
            self._lsl_streaming_enabled.set()
            print("LSL stream resumed with updated board.")
            self.status_changed.emit("LSL stream resumed")


    def stop_stream(self):
        if hasattr(self, '_lsl_streaming_enabled') and self._lsl_streaming_enabled.is_set():
            # Instead of terminating the thread, pause streaming.
            self._lsl_streaming_enabled.clear()
            print("LSL stream paused.")
            self.status_changed.emit("LSL stream paused")
        # Commented below out because adding it will cause the LSL thread to run to the end and not be paused but killed.
        # if hasattr(self, '_lsl_stay_alive') and self._lsl_stay_alive.is_set():
            # Instead of terminating the thread, pause streaming.
            # self._lsl_stay_alive.clear()
            # print("LSL stream thread killed.")
            # self.status_changed.emit("LSL stream paused")

    def kill_publisher(self):
        """
        Permanently kill the publisher thread, used only on full app shutdown.
        """
        if hasattr(self, '_lsl_stay_alive') and self._lsl_stay_alive.is_set():
            self._lsl_stay_alive.clear()
            print("LSL publisher thread forcibly killed.")
            if self.lsl_publisher and self.lsl_publisher.is_alive():
                self.lsl_publisher.join(timeout=2.0)
            self.lsl_publisher = None

    def get_status(self):
        if not self.connected and not self.auto_reconnect_enabled:
            return "Disconnected"
        elif self.handler and self.handler.is_alive():
            return "Alive"
        else:
            return "Not Alive. Attempting automatic reconnection."

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
            if self.auto_reconnect_enabled and current_status.startswith("Not Alive"):
                now = time.time()
                if now - self._last_reconnect_attempt >= self.reconnect_interval:
                    self._last_reconnect_attempt = now
                    if self.handler:
                        print("Connection lost. Cleaning up sessions.")
                        self.stop_stream()
                        time.sleep(1.0)  # Allow time for the stream to stop
                        self.handler.delete_board()
                        # Fully clean up lingering sessions:
                        BoardShim.release_all_sessions()
                    print("Auto-reconnect: attempting to reconnect sensor.")
                    self.connect()  # Expected to be non-blocking (or spawn its own thread)
            time.sleep(10)