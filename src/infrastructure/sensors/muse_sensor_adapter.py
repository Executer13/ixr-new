"""
Muse Sensor Adapter - Adapts MuseSensor to ISensor interface.

This adapter wraps the existing MuseSensor implementation and provides
the ISensor interface for integration with the new architecture.
"""

from src.domain.interfaces.i_sensor import ISensor
from src.common.constants.sensor_constants import SensorType, SensorStatus
from src.common.exceptions.exceptions import (
    SensorException,
    SensorConnectionError,
    SensorNotConnectedError,
    SensorStreamingError
)
from src.common.utils.logger import get_logger

# Import the MuseSensor from the new architecture
from src.infrastructure.sensors.muse_sensor import MuseSensor as LegacyMuseSensor

logger = get_logger(__name__)


class MuseSensorAdapter(ISensor):
    """
    Adapter for MuseSensor that implements ISensor interface.

    This adapter wraps the legacy MuseSensor implementation and provides
    the standard ISensor interface for the new architecture.

    Signals:
        status_changed: Emitted when sensor status changes (inherited from ISensor)
    """

    def __init__(self):
        """Initialize the Muse sensor adapter."""
        super().__init__()
        self._sensor = LegacyMuseSensor()
        self._status = SensorStatus.DISCONNECTED.value
        self._is_connected = False
        self._is_streaming = False

        # Connect to the legacy sensor's status signal
        self._sensor.status_changed.connect(self._handle_status_change)

        logger.info("MuseSensorAdapter initialized")

    def connect(self) -> None:
        """
        Establish connection to the Muse sensor hardware.

        This method initiates connection in a non-blocking manner.

        Raises:
            SensorConnectionError: If connection initiation fails
        """
        try:
            logger.info("Connecting to Muse sensor")
            self._sensor.connect()
            # Status updates will come through status_changed signal

        except Exception as e:
            error_msg = f"Failed to initiate Muse connection: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SensorConnectionError(error_msg)

    def disconnect(self) -> None:
        """
        Disconnect from the Muse sensor hardware.

        This method properly cleans up resources and stops any
        background threads or streams.
        """
        try:
            logger.info("Disconnecting Muse sensor")
            self._sensor.disconnect()
            self._is_connected = False
            self._is_streaming = False
            self._status = SensorStatus.DISCONNECTED.value

        except Exception as e:
            error_msg = f"Error disconnecting Muse sensor: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Don't raise exception on disconnect, just log it
            self.status_changed.emit(f"Error: {error_msg}")

    def start_stream(self) -> None:
        """
        Begin streaming data from the Muse sensor.

        Raises:
            SensorNotConnectedError: If sensor is not connected
            SensorStreamingError: If streaming cannot be started
        """
        if not self._is_connected:
            raise SensorNotConnectedError("Muse sensor is not connected")

        try:
            logger.info("Starting Muse stream")
            self._sensor.start_stream()
            # Status updates will come through status_changed signal

        except Exception as e:
            error_msg = f"Failed to start Muse stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SensorStreamingError(error_msg)

    def stop_stream(self) -> None:
        """
        Stop streaming data from the Muse sensor.

        Raises:
            SensorNotConnectedError: If sensor is not connected
        """
        if not self._is_connected:
            raise SensorNotConnectedError("Muse sensor is not connected")

        try:
            logger.info("Stopping Muse stream")
            self._sensor.stop_stream()
            self._is_streaming = False
            self.status_changed.emit("LSL stream paused")

        except Exception as e:
            error_msg = f"Error stopping Muse stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.status_changed.emit(f"Error: {error_msg}")

    def get_status(self) -> str:
        """
        Get the current status of the Muse sensor.

        Returns:
            str: Human-readable status message
        """
        return self._status

    def is_connected(self) -> bool:
        """
        Check if the Muse sensor is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self._is_connected

    def is_streaming(self) -> bool:
        """
        Check if the Muse sensor is currently streaming data.

        Returns:
            bool: True if streaming, False otherwise
        """
        return self._is_streaming

    @property
    def sensor_type(self) -> str:
        """
        Get the type/name of this sensor.

        Returns:
            str: Sensor type identifier
        """
        return SensorType.MUSE_S.value

    def get_board_shim(self):
        """
        Get the BrainFlow BoardShim instance.

        This is a helper method for components that need direct access
        to the BoardShim (like the brain power analysis module).

        Returns:
            BoardShim instance or None if not connected
        """
        if hasattr(self._sensor, 'handler') and self._sensor.handler:
            return self._sensor.handler.board
        return None

    def kill_publisher(self) -> None:
        """
        Kill the LSL publisher thread.

        This is a helper method for cleanup during application shutdown.
        """
        try:
            if hasattr(self._sensor, 'lsl_publisher') and self._sensor.lsl_publisher:
                logger.info("Killing Muse LSL publisher")
                if hasattr(self._sensor, '_lsl_stay_alive'):
                    self._sensor._lsl_stay_alive.clear()
                # Give it a moment to stop
                import time
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error killing LSL publisher: {e}")

    def _handle_status_change(self, status: str) -> None:
        """
        Handle status changes from the legacy sensor.

        Args:
            status: Status message from the legacy sensor
        """
        self._status = status
        logger.debug(f"Muse status changed: {status}")

        # Update connection state based on status
        status_lower = status.lower()

        if any(x in status_lower for x in ["connected", "alive", "lsl stream started", "lsl stream resumed"]):
            self._is_connected = True
            if "stream" in status_lower:
                self._is_streaming = True
        elif "disconnected" in status_lower or "connection failed" in status_lower:
            self._is_connected = False
            self._is_streaming = False
        elif "lsl stream paused" in status_lower:
            self._is_streaming = False

        # Forward the status signal
        self.status_changed.emit(status)

    def __del__(self):
        """Cleanup when adapter is destroyed."""
        try:
            if self._is_connected:
                self.disconnect()
        except:
            pass
