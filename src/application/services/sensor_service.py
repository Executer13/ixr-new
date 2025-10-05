"""
Sensor Service - High-level sensor management service.

This service provides a unified interface for managing multiple sensors,
handling connections, status monitoring, and event coordination.
"""

from typing import Dict, List, Optional
from PyQt5.QtCore import QObject
import logging

from src.domain.interfaces.i_sensor import ISensor
from src.infrastructure.sensors.sensor_factory import SensorFactory
from src.domain.events.event_bus import get_event_bus
from src.domain.events.sensor_events import (
    SensorConnectedEvent, SensorDisconnectedEvent,
    SensorStatusChangedEvent, SensorErrorEvent
)
from src.common.constants.sensor_constants import SensorType, SensorStatus
from src.common.exceptions.exceptions import (
    SensorException, SensorNotConnectedError
)

logger = logging.getLogger(__name__)


class SensorService(QObject):
    """
    Sensor Management Service.

    Provides centralized management of multiple sensors, including:
    - Sensor lifecycle management (create, connect, disconnect)
    - Status monitoring and event coordination
    - Multi-sensor operations
    """

    def __init__(self, sensor_factory: SensorFactory):
        """
        Initialize the sensor service.

        Args:
            sensor_factory: Factory for creating sensor instances
        """
        super().__init__()
        self._sensor_factory = sensor_factory
        self._sensors: Dict[str, ISensor] = {}
        self._event_bus = get_event_bus()
        logger.info("SensorService initialized")

    def create_sensor(self, sensor_type: SensorType, sensor_id: str) -> ISensor:
        """
        Create a new sensor instance.

        Args:
            sensor_type: Type of sensor to create
            sensor_id: Unique identifier for this sensor instance

        Returns:
            ISensor: Created sensor instance

        Raises:
            SensorException: If sensor creation fails
        """
        try:
            logger.info(f"Creating sensor: {sensor_type.value} (ID: {sensor_id})")

            # Create sensor using factory
            sensor = self._sensor_factory.create_sensor(sensor_type)

            # Store sensor
            self._sensors[sensor_id] = sensor

            # Wire up status change events
            sensor.status_changed.connect(
                lambda status: self._handle_sensor_status_change(sensor_id, status)
            )

            logger.info(f"Sensor created successfully: {sensor_id}")
            return sensor

        except Exception as e:
            logger.error(f"Failed to create sensor '{sensor_id}': {e}", exc_info=True)
            raise SensorException(f"Failed to create sensor: {str(e)}")

    def get_sensor(self, sensor_id: str) -> Optional[ISensor]:
        """
        Get a sensor by its ID.

        Args:
            sensor_id: ID of the sensor

        Returns:
            ISensor if found, None otherwise
        """
        return self._sensors.get(sensor_id)

    def connect_sensor(self, sensor_id: str) -> None:
        """
        Connect a sensor.

        Args:
            sensor_id: ID of the sensor to connect

        Raises:
            SensorNotConnectedError: If sensor doesn't exist
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise SensorNotConnectedError(f"Sensor not found: {sensor_id}")

        logger.info(f"Connecting sensor: {sensor_id}")
        sensor.connect()

    def disconnect_sensor(self, sensor_id: str) -> None:
        """
        Disconnect a sensor.

        Args:
            sensor_id: ID of the sensor to disconnect

        Raises:
            SensorNotConnectedError: If sensor doesn't exist
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise SensorNotConnectedError(f"Sensor not found: {sensor_id}")

        logger.info(f"Disconnecting sensor: {sensor_id}")
        sensor.disconnect()

    def start_streaming(self, sensor_id: str) -> None:
        """
        Start streaming data from a sensor.

        Args:
            sensor_id: ID of the sensor

        Raises:
            SensorNotConnectedError: If sensor doesn't exist or not connected
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise SensorNotConnectedError(f"Sensor not found: {sensor_id}")

        if not sensor.is_connected():
            raise SensorNotConnectedError(f"Sensor not connected: {sensor_id}")

        logger.info(f"Starting stream for sensor: {sensor_id}")
        sensor.start_stream()

    def stop_streaming(self, sensor_id: str) -> None:
        """
        Stop streaming data from a sensor.

        Args:
            sensor_id: ID of the sensor

        Raises:
            SensorNotConnectedError: If sensor doesn't exist
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise SensorNotConnectedError(f"Sensor not found: {sensor_id}")

        logger.info(f"Stopping stream for sensor: {sensor_id}")
        sensor.stop_stream()

    def get_sensor_status(self, sensor_id: str) -> Optional[str]:
        """
        Get the current status of a sensor.

        Args:
            sensor_id: ID of the sensor

        Returns:
            str: Status message, or None if sensor not found
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            return None

        return sensor.get_status()

    def is_sensor_connected(self, sensor_id: str) -> bool:
        """
        Check if a sensor is connected.

        Args:
            sensor_id: ID of the sensor

        Returns:
            bool: True if connected, False otherwise
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            return False

        return sensor.is_connected()

    def is_sensor_streaming(self, sensor_id: str) -> bool:
        """
        Check if a sensor is streaming.

        Args:
            sensor_id: ID of the sensor

        Returns:
            bool: True if streaming, False otherwise
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            return False

        return sensor.is_streaming()

    def get_all_sensors(self) -> Dict[str, ISensor]:
        """
        Get all registered sensors.

        Returns:
            Dict[str, ISensor]: Dictionary of sensor ID to sensor instance
        """
        return self._sensors.copy()

    def get_connected_sensors(self) -> List[str]:
        """
        Get IDs of all connected sensors.

        Returns:
            List[str]: List of sensor IDs
        """
        return [
            sensor_id for sensor_id, sensor in self._sensors.items()
            if sensor.is_connected()
        ]

    def disconnect_all(self) -> None:
        """Disconnect all sensors."""
        logger.info("Disconnecting all sensors")

        for sensor_id, sensor in self._sensors.items():
            if sensor.is_connected():
                try:
                    sensor.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting sensor '{sensor_id}': {e}")

    def cleanup(self) -> None:
        """Clean up the service and all sensors."""
        logger.info("Cleaning up sensor service")

        self.disconnect_all()
        self._sensors.clear()

        logger.info("Sensor service cleanup complete")

    def _handle_sensor_status_change(self, sensor_id: str, status: str) -> None:
        """
        Handle sensor status change and publish appropriate events.

        Args:
            sensor_id: ID of the sensor
            status: New status message
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            return

        logger.debug(f"Sensor '{sensor_id}' status changed: {status}")

        # Publish status changed event
        event = SensorStatusChangedEvent(
            sensor_type=sensor.sensor_type,
            sensor_id=sensor_id,
            status=status
        )
        self._event_bus.publish(event)

        # Publish specific events based on status
        if "connected" in status.lower():
            connected_event = SensorConnectedEvent(
                sensor_type=sensor.sensor_type,
                sensor_id=sensor_id
            )
            self._event_bus.publish(connected_event)

        elif "disconnected" in status.lower():
            disconnected_event = SensorDisconnectedEvent(
                sensor_type=sensor.sensor_type,
                sensor_id=sensor_id
            )
            self._event_bus.publish(disconnected_event)

        elif "error" in status.lower():
            error_event = SensorErrorEvent(
                sensor_type=sensor.sensor_type,
                sensor_id=sensor_id,
                error=status
            )
            self._event_bus.publish(error_event)
