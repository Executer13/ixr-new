"""
Sensor Interface - Defines the contract for all sensor implementations.

This interface ensures all sensors follow the same protocol for connection,
disconnection, streaming, and status monitoring.
"""

from abc import ABCMeta, abstractmethod
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QObject


# Create a compatible metaclass that combines QObject and ABC
class QABCMeta(type(QObject), ABCMeta):
    """Metaclass that combines Qt's metaclass with ABC's metaclass."""
    pass


class ISensor(QObject, metaclass=QABCMeta):
    """
    Abstract base class for all sensor implementations.

    Sensors are responsible for:
    - Establishing connections to hardware devices
    - Managing data streaming
    - Monitoring connection health
    - Providing status updates via signals

    Attributes:
        status_changed (pyqtSignal): Signal emitted when sensor status changes
    """

    status_changed = pyqtSignal(str)

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the sensor hardware.

        This method should be non-blocking and emit status_changed signals
        to indicate connection progress.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the sensor hardware.

        This method should properly clean up resources and stop any
        background threads or streams.
        """
        pass

    @abstractmethod
    def start_stream(self) -> None:
        """
        Begin streaming data from the sensor.

        Raises:
            RuntimeError: If sensor is not connected
        """
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """
        Stop streaming data from the sensor.

        Raises:
            RuntimeError: If sensor is not connected
        """
        pass

    @abstractmethod
    def get_status(self) -> str:
        """
        Get the current status of the sensor.

        Returns:
            str: Human-readable status message
                (e.g., "Connected", "Disconnected", "Streaming")
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the sensor is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        """
        Check if the sensor is currently streaming data.

        Returns:
            bool: True if streaming, False otherwise
        """
        pass

    @property
    @abstractmethod
    def sensor_type(self) -> str:
        """
        Get the type/name of this sensor.

        Returns:
            str: Sensor type identifier (e.g., "Muse", "Polar H10")
        """
        pass
