"""
Muse Sensor - Infrastructure component for Muse EEG headband.

This module provides the Muse sensor implementation using BrainFlow,
with LSL streaming and automatic reconnection capabilities.
"""

import threading
from threading import Event
import time

from src.domain.interfaces.sensor_interface import SensorInterface
from src.infrastructure.sensors.brainflow_handler import BrainFlowHandler
from src.infrastructure.streaming.brainflow_lsl_publisher import BrainFlowLSLPublisher
from brainflow.board_shim import BrainFlowInputParams, BoardIds, BoardShim

from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class MuseSensor(SensorInterface):
    """
    Muse EEG headband sensor implementation.

    Connects to Muse S via BrainFlow, streams data to LSL,
    and provides automatic reconnection on connection loss.
    """

    def __init__(self):
        super(MuseSensor, self).__init__()
        self.board_id = BoardIds.MUSE_S_BOARD.value
        self.input_params = BrainFlowInputParams()
        self.handler = None
        self.auto_reconnect_enabled = True
        self._connecting = False
        self._disconnecting = False

    def connect(self):
        """Connect to the Muse sensor in a background thread."""
        logger.debug("connect() called")

        # Prevent concurrent connection attempts
        if self._connecting:
            logger.warning("Already connecting, ignoring duplicate request")
            return
        if self._disconnecting:
            logger.warning("Currently disconnecting, cannot connect yet")
            return

        self.auto_reconnect_enabled = True
        self._connecting = True

        def connect_worker():
            logger.debug("connect_worker started")
            try:
                # Ensure any lingering sessions are released before connecting
                logger.debug("Releasing any lingering sessions...")
                BoardShim.release_all_sessions()
                time.sleep(1.0)  # Allow time for complete cleanup

                logger.debug("Creating BrainFlowHandler...")
                self.handler = BrainFlowHandler(self.board_id, self.input_params)
                logger.debug("Calling prepare_and_connect_board...")
                self.handler.prepare_and_connect_board()
                logger.debug("Board prepared, sleeping 2 seconds...")
                time.sleep(2.0)  # Allow some time for the handler to update its status
                is_alive = self.handler.is_alive()
                logger.debug(f"handler.is_alive() = {is_alive}")
                if is_alive:
                    self.connected = True
                    self.status_changed.emit("Connected")
                    logger.info("MuseSensor: Connected via BrainFlowHandler")
                    logger.debug("About to call start_status_check...")
                    self.start_status_check()
                    logger.debug("About to call start_stream...")
                    self.start_stream()
                    logger.debug("start_stream returned")
                else:
                    self.connected = False
                    error_message = "Connection failed: Board not ready"
                    self.status_changed.emit(error_message)
                    logger.error(f"MuseSensor: {error_message}")
            except Exception as e:
                self.connected = False
                error_message = f"Connection failed: {str(e)}"
                self.status_changed.emit(error_message)
                logger.error(f"MuseSensor: Connection failed: {e}", exc_info=True)
            finally:
                self._connecting = False
        threading.Thread(target=connect_worker, daemon=True).start()

    def disconnect(self):
        """Disconnect from the Muse sensor."""
        # Disable auto-reconnect to prevent immediate reconnection.
        self.auto_reconnect_enabled = False
        self._disconnecting = True
        self.stop_status_check()

        def disconnect_worker():
            try:
                if self.handler:
                    self.stop_stream()
                    time.sleep(1.0)  # Allow time for the stream to stop
                    self.handler.delete_board()
                    # Fully clean up lingering sessions:
                    BoardShim.release_all_sessions()
                    logger.info("MuseSensor: Disconnected successfully")
                    self.status_changed.emit("Disconnected")
                    self._last_status = "Disconnected"
            except Exception as e:
                error_message = f"Error during disconnect: {str(e)}"
                self.status_changed.emit(error_message)
                logger.error(f"MuseSensor: Error during disconnect: {e}", exc_info=True)
            finally:
                self.connected = False
                self.handler = None
                self._disconnecting = False
            # Optionally, wait a few seconds to ensure complete cleanup before allowing reconnection.
            time.sleep(2.0)
        threading.Thread(target=disconnect_worker, daemon=True).start()

    def start_stream(self):
        """Start LSL streaming from the Muse sensor."""
        logger.debug(f"start_stream called. connected={self.connected}")
        if not self.connected:
            raise Exception("MuseSensor not connected.")

        logger.debug(f"handler={self.handler}, handler.board={self.handler.board if self.handler else None}")

        # If no publisher exists, create one; otherwise, update its board and resume streaming.
        if not hasattr(self, 'lsl_publisher') or self.lsl_publisher is None:
            logger.debug("Creating NEW LSL publisher...")

            self._lsl_stay_alive = Event()
            self._lsl_stay_alive.set()
            self._lsl_streaming_enabled = Event()
            self._lsl_streaming_enabled.set()

            logger.debug(f"About to create BrainFlowLSLPublisher with board_shim={self.handler.board}")
            self.lsl_publisher = BrainFlowLSLPublisher(
                board_shim=self.handler.board,
                stay_alive=self._lsl_stay_alive,
                streaming_enabled=self._lsl_streaming_enabled
            )
            logger.debug("BrainFlowLSLPublisher created, starting thread...")
            self.lsl_publisher.start()
            logger.info("LSL publisher thread started")
            logger.info("LSL stream started")
            self.status_changed.emit("LSL stream started")
        else:
            logger.debug("LSL publisher already exists, updating board...")
            # Update the publisher's board with the current board from the handler.
            self.lsl_publisher.update_board(self.handler.board)
            # Resume streaming by ensuring the streaming_enabled event is set.
            self._lsl_streaming_enabled.set()
            logger.info("LSL stream resumed with updated board")
            self.status_changed.emit("LSL stream resumed")

    def stop_stream(self):
        """Pause LSL streaming."""
        if hasattr(self, '_lsl_streaming_enabled') and self._lsl_streaming_enabled.is_set():
            # Instead of terminating the thread, pause streaming.
            self._lsl_streaming_enabled.clear()
            logger.info("LSL stream paused")
            self.status_changed.emit("LSL stream paused")

    def kill_publisher(self):
        """
        Permanently kill the publisher thread, used only on full app shutdown.
        """
        if hasattr(self, '_lsl_stay_alive') and self._lsl_stay_alive.is_set():
            self._lsl_stay_alive.clear()
            logger.warning("LSL publisher thread forcibly killed")
            if self.lsl_publisher and self.lsl_publisher.is_alive():
                self.lsl_publisher.join(timeout=2.0)
            self.lsl_publisher = None

    def get_status(self):
        """Get the current status of the sensor."""
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

                    # Don't reconnect if already connecting/disconnecting
                    if self._connecting or self._disconnecting:
                        logger.debug("Auto-reconnect: skipping, connection state change in progress")
                    else:
                        logger.warning("Connection lost. Cleaning up sessions")
                        if self.handler:
                            try:
                                self.stop_stream()
                                time.sleep(1.0)  # Allow time for the stream to stop
                                self.handler.delete_board()
                            except Exception as e:
                                logger.error(f"Error during auto-reconnect cleanup: {e}")
                            finally:
                                self.handler = None

                        # Fully clean up lingering sessions
                        try:
                            BoardShim.release_all_sessions()
                        except Exception as e:
                            logger.error(f"Error releasing sessions: {e}")

                        # Wait for complete cleanup before reconnecting
                        logger.info("Auto-reconnect: waiting 3 seconds for session cleanup...")
                        time.sleep(3.0)

                        logger.info("Auto-reconnect: attempting to reconnect sensor")
                        self.connect()  # Expected to be non-blocking (or spawn its own thread)
            time.sleep(10)
