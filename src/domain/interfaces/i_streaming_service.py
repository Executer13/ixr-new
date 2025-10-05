"""
Streaming Service Interface - Defines the contract for LSL streaming services.

This interface ensures consistent stream management across different
streaming implementations.
"""

from abc import ABCMeta, abstractmethod
from typing import List, Optional, Any
from pylsl import StreamInfo
from PyQt5.QtCore import QObject


# Create a compatible metaclass that combines QObject and ABC
class QABCMeta(type(QObject), ABCMeta):
    """Metaclass that combines Qt's metaclass with ABC's metaclass."""
    pass


class IStreamingService(QObject, metaclass=QABCMeta):
    """
    Abstract base class for streaming service implementations.

    Streaming services are responsible for:
    - Discovering available LSL streams
    - Managing stream subscriptions
    - Providing stream information
    - Publishing sensor data to LSL
    """

    @abstractmethod
    def get_available_streams(self) -> List[StreamInfo]:
        """
        Get a list of all available LSL streams on the network.

        Returns:
            List[StreamInfo]: List of discovered stream information objects
        """
        pass

    @abstractmethod
    def create_outlet(self, name: str, stream_type: str,
                     channel_count: int, sampling_rate: float,
                     channel_names: Optional[List[str]] = None) -> Any:
        """
        Create a new LSL outlet for publishing data.

        Args:
            name: Name of the stream
            stream_type: Type of data (e.g., "EEG", "ECG", "Gyro")
            channel_count: Number of channels in the stream
            sampling_rate: Nominal sampling rate in Hz
            channel_names: Optional list of channel names

        Returns:
            StreamOutlet: The created LSL outlet
        """
        pass

    @abstractmethod
    def create_inlet(self, stream_info: StreamInfo) -> Any:
        """
        Create a new LSL inlet for receiving data from a stream.

        Args:
            stream_info: Information about the stream to connect to

        Returns:
            StreamInlet: The created LSL inlet
        """
        pass

    @abstractmethod
    def publish_data(self, outlet: Any, data: List[float],
                     timestamp: Optional[float] = None) -> None:
        """
        Publish data to an LSL outlet.

        Args:
            outlet: The LSL outlet to publish to
            data: The data samples to publish
            timestamp: Optional timestamp for the data
        """
        pass

    @abstractmethod
    def resolve_stream_by_name(self, name: str, timeout: float = 1.0) -> Optional[StreamInfo]:
        """
        Resolve a stream by its name.

        Args:
            name: Name of the stream to find
            timeout: Maximum time to wait in seconds

        Returns:
            StreamInfo if found, None otherwise
        """
        pass
