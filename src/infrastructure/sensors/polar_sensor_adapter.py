"""
Polar Sensor Adapter - Adapts PolarSensor to ISensor interface.

This adapter wraps the existing PolarSensor implementation and provides
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

# Import the PolarSensor from the new architecture
from src.infrastructure.sensors.polar_sensor import PolarSensor as LegacyPolarSensor

logger = get_logger(__name__)


class PolarSensorAdapter(ISensor):
    """
    Adapter for PolarSensor that implements ISensor interface.

    This adapter wraps the legacy PolarSensor implementation and provides
    the standard ISensor interface for the new architecture.

    Signals:
        status_changed: Emitted when sensor status changes (inherited from ISensor)
    """

    def __init__(self):
        """Initialize the Polar sensor adapter."""
        super().__init__()
        self._sensor = LegacyPolarSensor()
        self._status = SensorStatus.DISCONNECTED.value
        self._is_connected = False
        self._is_streaming = False

        # Connect to the legacy sensor's status signal
        self._sensor.status_changed.connect(self._handle_status_change)

        logger.info("PolarSensorAdapter initialized")

    def connect(self) -> None:
        """
        Establish connection to the Polar H10 sensor hardware.

        This method initiates connection in a non-blocking manner.

        Raises:
            SensorConnectionError: If connection initiation fails
        """
        try:
            logger.info("Connecting to Polar H10 sensor")
            self._sensor.connect()
            # Status updates will come through status_changed signal

        except Exception as e:
            error_msg = f"Failed to initiate Polar connection: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SensorConnectionError(error_msg)

    def disconnect(self) -> None:
        """
        Disconnect from the Polar H10 sensor hardware.

        This method properly cleans up resources and stops any
        background threads or streams.
        """
        try:
            logger.info("Disconnecting Polar H10 sensor")
            self._sensor.disconnect()
            self._is_connected = False
            self._is_streaming = False
            self._status = SensorStatus.DISCONNECTED.value

        except Exception as e:
            error_msg = f"Error disconnecting Polar sensor: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Don't raise exception on disconnect, just log it
            self.status_changed.emit(f"Error: {error_msg}")

    def start_stream(self) -> None:
        """
        Begin streaming data from the Polar sensor.

        Raises:
            SensorNotConnectedError: If sensor is not connected
            SensorStreamingError: If streaming cannot be started
        """
        if not self._is_connected:
            raise SensorNotConnectedError("Polar sensor is not connected")

        try:
            logger.info("Starting Polar stream")
            self._sensor.start_stream()
            # Status updates will come through status_changed signal

        except Exception as e:
            error_msg = f"Failed to start Polar stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SensorStreamingError(error_msg)

    def stop_stream(self) -> None:
        """
        Stop streaming data from the Polar sensor.

        Raises:
            SensorNotConnectedError: If sensor is not connected
        """
        if not self._is_connected:
            raise SensorNotConnectedError("Polar sensor is not connected")

        try:
            logger.info("Stopping Polar stream")
            self._sensor.stop_stream()
            self._is_streaming = False
            self.status_changed.emit("Stream stopped")

        except Exception as e:
            error_msg = f"Error stopping Polar stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.status_changed.emit(f"Error: {error_msg}")

    def get_status(self) -> str:
        """
        Get the current status of the Polar sensor.

        Returns:
            str: Human-readable status message
        """
        return self._status

    def is_connected(self) -> bool:
        """
        Check if the Polar sensor is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self._is_connected

    def is_streaming(self) -> bool:
        """
        Check if the Polar sensor is currently streaming data.

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
        return SensorType.POLAR_H10.value

    def _handle_status_change(self, status: str) -> None:
        """
        Handle status changes from the legacy sensor.

        Args:
            status: Status message from the legacy sensor
        """
        self._status = status
        logger.debug(f"Polar status changed: {status}")

        # Update connection state based on status
        status_lower = status.lower()

        if "connected" in status_lower or "alive" in status_lower:
            self._is_connected = True
        elif "ecg data is now arriving" in status_lower:
            self._is_connected = True
            self._is_streaming = True
        elif "disconnected" in status_lower or "connection failed" in status_lower:
            self._is_connected = False
            self._is_streaming = False
        elif "lsl stream created" in status_lower:
            # Stream created but may not be streaming yet
            pass

        # Forward the status signal
        self.status_changed.emit(status)

    def __del__(self):
        """Cleanup when adapter is destroyed."""
        try:
            if self._is_connected:
                self.disconnect()
        except:
            pass
