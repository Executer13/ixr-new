"""
Stream Events - Domain events for streaming operations.

This module defines all events related to LSL streaming.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from .event_bus import Event


class StreamEventTypes:
    """Event type constants for stream events."""
    STREAM_DISCOVERED = "stream.discovered"
    STREAM_ADDED = "stream.added"
    STREAM_REMOVED = "stream.removed"
    STREAM_DATA_RECEIVED = "stream.data.received"
    ALL_STREAMS_REMOVED = "stream.all.removed"


@dataclass
class StreamDiscoveredEvent(Event):
    """Event emitted when a new stream is discovered."""

    def __init__(self, stream_name: str, stream_type: str, channel_count: int):
        super().__init__(
            timestamp=datetime.now(),
            event_type=StreamEventTypes.STREAM_DISCOVERED,
            source="streaming_service",
            data={
                "stream_name": stream_name,
                "stream_type": stream_type,
                "channel_count": channel_count
            }
        )


@dataclass
class StreamAddedEvent(Event):
    """Event emitted when a stream is added to plotting."""

    def __init__(self, stream_name: str, stream_type: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=StreamEventTypes.STREAM_ADDED,
            source="plot_service",
            data={
                "stream_name": stream_name,
                "stream_type": stream_type
            }
        )


@dataclass
class StreamRemovedEvent(Event):
    """Event emitted when a stream is removed from plotting."""

    def __init__(self, stream_name: str, stream_type: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=StreamEventTypes.STREAM_REMOVED,
            source="plot_service",
            data={
                "stream_name": stream_name,
                "stream_type": stream_type
            }
        )


@dataclass
class AllStreamsRemovedEvent(Event):
    """Event emitted when all streams are removed."""

    def __init__(self):
        super().__init__(
            timestamp=datetime.now(),
            event_type=StreamEventTypes.ALL_STREAMS_REMOVED,
            source="plot_service",
            data={}
        )
