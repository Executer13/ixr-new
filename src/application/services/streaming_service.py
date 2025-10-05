"""
Streaming Service - Manages LSL streaming operations.

This service provides a high-level API for managing LSL streams,
coordinating stream discovery, subscription, and data flow.
"""

from typing import List, Dict, Optional, Any
from PyQt5.QtCore import pyqtSignal
from pylsl import StreamInfo, StreamInlet, StreamOutlet, resolve_streams, local_clock

from src.domain.interfaces.i_streaming_service import IStreamingService
from src.domain.events.event_bus import get_event_bus
from src.domain.events.stream_events import (
    StreamDiscoveredEvent,
    StreamAddedEvent,
    StreamRemovedEvent,
    AllStreamsRemovedEvent
)
from src.common.constants.app_constants import LSLDefaults
from src.common.exceptions.exceptions import (
    StreamingException,
    StreamNotFoundException,
    StreamCreationError
)
from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class StreamingService(IStreamingService):
    """
    Service for managing LSL streaming operations.

    Responsibilities:
    - Discover available LSL streams
    - Create and manage inlets/outlets
    - Track active streams
    - Publish stream events
    - Handle streaming errors

    Signals:
        streams_discovered: Emitted when new streams are discovered
        stream_added: Emitted when a stream is added for plotting
        stream_removed: Emitted when a stream is removed
    """

    streams_discovered = pyqtSignal(list)  # List[StreamInfo]
    stream_added = pyqtSignal(object)  # StreamInfo
    stream_removed = pyqtSignal(object)  # StreamInfo

    def __init__(self):
        """Initialize the streaming service."""
        super().__init__()
        self._outlets: Dict[str, StreamOutlet] = {}
        self._inlets: Dict[str, StreamInlet] = {}
        self._active_streams: Dict[str, StreamInfo] = {}
        self._event_bus = get_event_bus()
        logger.info("StreamingService initialized")

    def get_available_streams(self) -> List[StreamInfo]:
        """
        Get a list of all available LSL streams on the network.

        Returns:
            List[StreamInfo]: List of discovered stream information objects
        """
        try:
            logger.debug("Resolving LSL streams...")
            streams = resolve_streams()

            # Publish discovery events
            for stream in streams:
                event = StreamDiscoveredEvent(
                    stream.name(),
                    stream.type(),
                    stream.channel_count()
                )
                self._event_bus.publish(event)

            logger.info(f"Found {len(streams)} LSL streams")
            self.streams_discovered.emit(streams)

            return streams

        except Exception as e:
            logger.error(f"Error resolving streams: {e}")
            raise StreamingException(f"Failed to resolve streams: {str(e)}")

    def create_outlet(self, name: str, stream_type: str,
                     channel_count: int, sampling_rate: float,
                     channel_names: Optional[List[str]] = None) -> StreamOutlet:
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

        Raises:
            StreamCreationError: If outlet creation fails
        """
        try:
            # Create stream info
            info = StreamInfo(
                name=name,
                type=stream_type,
                channel_count=channel_count,
                nominal_srate=sampling_rate,
                channel_format='float32',
                source_id=LSLDefaults.SOURCE_ID
            )

            # Add channel information if provided
            if channel_names:
                channels = info.desc().append_child("channels")
                for ch_name in channel_names:
                    ch = channels.append_child("channel")
                    ch.append_child_value("label", ch_name)
                    ch.append_child_value("type", stream_type)

            # Create outlet
            outlet = StreamOutlet(info)

            # Store outlet
            outlet_id = self._generate_stream_id(name, stream_type)
            self._outlets[outlet_id] = outlet

            logger.info(f"Created LSL outlet: {name} ({stream_type})")

            return outlet

        except Exception as e:
            logger.error(f"Failed to create outlet {name}: {e}")
            raise StreamCreationError(f"Failed to create outlet: {str(e)}")

    def create_inlet(self, stream_info: StreamInfo) -> StreamInlet:
        """
        Create a new LSL inlet for receiving data from a stream.

        Args:
            stream_info: Information about the stream to connect to

        Returns:
            StreamInlet: The created LSL inlet

        Raises:
            StreamCreationError: If inlet creation fails
        """
        try:
            inlet = StreamInlet(stream_info)

            # Store inlet
            inlet_id = self._generate_stream_id(
                stream_info.name(),
                stream_info.type()
            )
            self._inlets[inlet_id] = inlet

            logger.info(f"Created LSL inlet: {stream_info.name()} "
                       f"({stream_info.type()})")

            return inlet

        except Exception as e:
            logger.error(f"Failed to create inlet: {e}")
            raise StreamCreationError(f"Failed to create inlet: {str(e)}")

    def publish_data(self, outlet: StreamOutlet, data: List[float],
                     timestamp: Optional[float] = None) -> None:
        """
        Publish data to an LSL outlet.

        Args:
            outlet: The LSL outlet to publish to
            data: The data samples to publish
            timestamp: Optional timestamp for the data

        Raises:
            StreamingException: If publishing fails
        """
        try:
            if timestamp is None:
                timestamp = local_clock()

            outlet.push_sample(data, timestamp)

        except Exception as e:
            logger.error(f"Error publishing data: {e}")
            raise StreamingException(f"Failed to publish data: {str(e)}")

    def resolve_stream_by_name(self, name: str,
                               timeout: float = LSLDefaults.RESOLVE_TIMEOUT
                               ) -> Optional[StreamInfo]:
        """
        Resolve a stream by its name.

        Args:
            name: Name of the stream to find
            timeout: Maximum time to wait in seconds

        Returns:
            StreamInfo if found, None otherwise
        """
        try:
            streams = resolve_streams()

            for stream in streams:
                if stream.name() == name:
                    logger.debug(f"Found stream: {name}")
                    return stream

            logger.debug(f"Stream not found: {name}")
            return None

        except Exception as e:
            logger.error(f"Error resolving stream {name}: {e}")
            return None

    def add_stream_to_plot(self, stream_info: StreamInfo) -> None:
        """
        Add a stream to the list of actively plotted streams.

        Args:
            stream_info: Information about the stream to add
        """
        stream_id = self._generate_stream_id(
            stream_info.name(),
            stream_info.type()
        )

        if stream_id not in self._active_streams:
            self._active_streams[stream_id] = stream_info

            # Emit signals
            self.stream_added.emit(stream_info)

            # Publish event
            event = StreamAddedEvent(stream_info.name(), stream_info.type())
            self._event_bus.publish(event)

            logger.info(f"Added stream to plot: {stream_info.name()}")

    def remove_stream_from_plot(self, stream_info: StreamInfo) -> None:
        """
        Remove a stream from the list of actively plotted streams.

        Args:
            stream_info: Information about the stream to remove
        """
        stream_id = self._generate_stream_id(
            stream_info.name(),
            stream_info.type()
        )

        if stream_id in self._active_streams:
            del self._active_streams[stream_id]

            # Emit signals
            self.stream_removed.emit(stream_info)

            # Publish event
            event = StreamRemovedEvent(stream_info.name(), stream_info.type())
            self._event_bus.publish(event)

            logger.info(f"Removed stream from plot: {stream_info.name()}")

    def remove_all_streams(self) -> None:
        """Remove all streams from plotting."""
        self._active_streams.clear()

        # Publish event
        event = AllStreamsRemovedEvent()
        self._event_bus.publish(event)

        logger.info("Removed all streams from plot")

    def get_active_streams(self) -> List[StreamInfo]:
        """
        Get list of actively plotted streams.

        Returns:
            List[StreamInfo]: List of active stream information objects
        """
        return list(self._active_streams.values())

    def is_stream_active(self, stream_info: StreamInfo) -> bool:
        """
        Check if a stream is actively being plotted.

        Args:
            stream_info: Stream to check

        Returns:
            bool: True if active, False otherwise
        """
        stream_id = self._generate_stream_id(
            stream_info.name(),
            stream_info.type()
        )
        return stream_id in self._active_streams

    def close_outlet(self, name: str, stream_type: str) -> None:
        """
        Close an LSL outlet.

        Args:
            name: Name of the stream
            stream_type: Type of the stream
        """
        outlet_id = self._generate_stream_id(name, stream_type)

        if outlet_id in self._outlets:
            del self._outlets[outlet_id]
            logger.info(f"Closed outlet: {name}")

    def close_inlet(self, name: str, stream_type: str) -> None:
        """
        Close an LSL inlet.

        Args:
            name: Name of the stream
            stream_type: Type of the stream
        """
        inlet_id = self._generate_stream_id(name, stream_type)

        if inlet_id in self._inlets:
            del self._inlets[inlet_id]
            logger.info(f"Closed inlet: {name}")

    def _generate_stream_id(self, name: str, stream_type: str) -> str:
        """
        Generate a unique identifier for a stream.

        Args:
            name: Stream name
            stream_type: Stream type

        Returns:
            str: Unique stream identifier
        """
        return f"{name}_{stream_type}"

    def cleanup(self) -> None:
        """Cleanup all outlets and inlets."""
        logger.info("Cleaning up StreamingService")

        # Close all outlets
        for outlet_id in list(self._outlets.keys()):
            del self._outlets[outlet_id]

        # Close all inlets
        for inlet_id in list(self._inlets.keys()):
            del self._inlets[inlet_id]

        # Clear active streams
        self._active_streams.clear()

        logger.info("StreamingService cleanup complete")
