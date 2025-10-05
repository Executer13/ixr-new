"""
Sensor Factory - Factory pattern for creating sensor instances.

This module provides a centralized way to create sensor instances,
abstracting the creation logic and promoting loose coupling.
"""

from typing import Optional, Dict, Any
from enum import Enum

from src.domain.interfaces.i_sensor import ISensor
from src.common.constants.sensor_constants import SensorType
from src.common.exceptions.exceptions import SensorConfigurationError


class SensorFactory:
    """
    Factory for creating sensor instances.

    Uses the Factory Pattern to create appropriate sensor implementations
    based on sensor type, hiding instantiation complexity from clients.
    """

    # Registry of sensor creators (will be populated when implementations are ready)
    _creators: Dict[SensorType, callable] = {}

    @classmethod
    def register_creator(cls, sensor_type: SensorType, creator: callable) -> None:
        """
        Register a sensor creator function.

        Args:
            sensor_type: The type of sensor this creator handles
            creator: Function that creates and returns a sensor instance

        Example:
            SensorFactory.register_creator(
                SensorType.MUSE,
                lambda: MuseSensor()
            )
        """
        cls._creators[sensor_type] = creator

    @classmethod
    def create_sensor(cls, sensor_type: SensorType,
                     config: Optional[Dict[str, Any]] = None) -> ISensor:
        """
        Create a sensor instance of the specified type.

        Args:
            sensor_type: The type of sensor to create
            config: Optional configuration dictionary for the sensor

        Returns:
            ISensor: A sensor instance implementing the ISensor interface

        Raises:
            SensorConfigurationError: If sensor type is not supported or
                                     configuration is invalid
        """
        if sensor_type not in cls._creators:
            raise SensorConfigurationError(
                f"Unsupported sensor type: {sensor_type}. "
                f"Available types: {list(cls._creators.keys())}"
            )

        creator = cls._creators[sensor_type]

        try:
            if config:
                # If creator accepts config, pass it
                sensor = creator(config)
            else:
                sensor = creator()

            return sensor

        except Exception as e:
            raise SensorConfigurationError(
                f"Failed to create sensor of type {sensor_type}: {str(e)}"
            )

    @classmethod
    def create_sensor_by_name(cls, sensor_name: str,
                             config: Optional[Dict[str, Any]] = None) -> ISensor:
        """
        Create a sensor instance by name string.

        Args:
            sensor_name: Name of the sensor (e.g., "Muse", "Polar H10")
            config: Optional configuration dictionary

        Returns:
            ISensor: A sensor instance

        Raises:
            SensorConfigurationError: If sensor name is not recognized
        """
        # Map common name variants to SensorType
        name_mapping = {
            "muse": SensorType.MUSE,
            "muse 2": SensorType.MUSE_2,
            "muse s": SensorType.MUSE_S,
            "muse_s": SensorType.MUSE_S,
            "polar": SensorType.POLAR_H10,
            "polar h10": SensorType.POLAR_H10,
            "polar_h10": SensorType.POLAR_H10,
        }

        sensor_name_lower = sensor_name.lower().strip()

        if sensor_name_lower not in name_mapping:
            raise SensorConfigurationError(
                f"Unknown sensor name: {sensor_name}. "
                f"Supported names: {list(name_mapping.keys())}"
            )

        sensor_type = name_mapping[sensor_name_lower]
        return cls.create_sensor(sensor_type, config)

    @classmethod
    def get_available_sensors(cls) -> list:
        """
        Get a list of available sensor types.

        Returns:
            list: List of SensorType enums for available sensors
        """
        return list(cls._creators.keys())

    @classmethod
    def is_sensor_available(cls, sensor_type: SensorType) -> bool:
        """
        Check if a sensor type is available.

        Args:
            sensor_type: The sensor type to check

        Returns:
            bool: True if sensor type is registered, False otherwise
        """
        return sensor_type in cls._creators


# Creator functions for sensor adapters
def _create_muse_sensor(config: Optional[Dict] = None) -> ISensor:
    """
    Create a Muse sensor instance.

    Args:
        config: Optional configuration (not currently used)

    Returns:
        ISensor: Muse sensor adapter instance
    """
    from src.infrastructure.sensors.muse_sensor_adapter import MuseSensorAdapter
    return MuseSensorAdapter()


def _create_polar_sensor(config: Optional[Dict] = None) -> ISensor:
    """
    Create a Polar H10 sensor instance.

    Args:
        config: Optional configuration (not currently used)

    Returns:
        ISensor: Polar sensor adapter instance
    """
    from src.infrastructure.sensors.polar_sensor_adapter import PolarSensorAdapter
    return PolarSensorAdapter()


# Register creators
SensorFactory.register_creator(SensorType.MUSE, _create_muse_sensor)
SensorFactory.register_creator(SensorType.MUSE_2, _create_muse_sensor)
SensorFactory.register_creator(SensorType.MUSE_S, _create_muse_sensor)
SensorFactory.register_creator(SensorType.POLAR_H10, _create_polar_sensor)
