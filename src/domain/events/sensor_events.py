"""
Sensor Events - Domain events for sensor operations.

This module defines all events related to sensor operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from .event_bus import Event


class SensorEventTypes:
    """Event type constants for sensor events."""
    SENSOR_CONNECTED = "sensor.connected"
    SENSOR_DISCONNECTED = "sensor.disconnected"
    SENSOR_STREAMING_STARTED = "sensor.streaming.started"
    SENSOR_STREAMING_STOPPED = "sensor.streaming.stopped"
    SENSOR_STATUS_CHANGED = "sensor.status.changed"
    SENSOR_ERROR = "sensor.error"
    SENSOR_DATA_RECEIVED = "sensor.data.received"


@dataclass
class SensorConnectedEvent(Event):
    """Event emitted when a sensor is connected."""

    def __init__(self, sensor_type: str, sensor_id: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_CONNECTED,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id
            }
        )


@dataclass
class SensorDisconnectedEvent(Event):
    """Event emitted when a sensor is disconnected."""

    def __init__(self, sensor_type: str, sensor_id: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_DISCONNECTED,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id
            }
        )


@dataclass
class SensorStreamingStartedEvent(Event):
    """Event emitted when sensor streaming starts."""

    def __init__(self, sensor_type: str, sensor_id: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_STREAMING_STARTED,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id
            }
        )


@dataclass
class SensorStreamingStoppedEvent(Event):
    """Event emitted when sensor streaming stops."""

    def __init__(self, sensor_type: str, sensor_id: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_STREAMING_STOPPED,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id
            }
        )


@dataclass
class SensorStatusChangedEvent(Event):
    """Event emitted when sensor status changes."""

    def __init__(self, sensor_type: str, sensor_id: str, status: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_STATUS_CHANGED,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id,
                "status": status
            }
        )


@dataclass
class SensorErrorEvent(Event):
    """Event emitted when a sensor error occurs."""

    def __init__(self, sensor_type: str, sensor_id: str, error: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=SensorEventTypes.SENSOR_ERROR,
            source=f"sensor.{sensor_type}",
            data={
                "sensor_type": sensor_type,
                "sensor_id": sensor_id,
                "error": error
            }
        )
