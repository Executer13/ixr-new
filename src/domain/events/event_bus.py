"""
Event Bus - Centralized event management system.

This module provides a publish-subscribe pattern for decoupled communication
between application components.
"""

from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
import logging


logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base class for all events."""
    timestamp: datetime
    event_type: str
    source: str
    data: Dict[str, Any]

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """
    Centralized event bus for publish-subscribe communication.

    The EventBus allows components to communicate without direct dependencies
    by publishing and subscribing to events.

    Thread-safe implementation for concurrent access.
    """

    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = Lock()

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Callback function to handle the event
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The callback function to remove
        """
        with self._lock:
            if event_type in self._subscribers:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    logger.debug(f"Unsubscribed from event: {event_type}")

                # Clean up empty subscriber lists
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        with self._lock:
            handlers = self._subscribers.get(event.event_type, []).copy()

        # Execute handlers outside the lock to prevent deadlocks
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.event_type}: {e}")

    def clear_subscribers(self, event_type: str = None) -> None:
        """
        Clear all subscribers for a specific event type or all events.

        Args:
            event_type: Specific event type to clear, or None to clear all
        """
        with self._lock:
            if event_type:
                if event_type in self._subscribers:
                    del self._subscribers[event_type]
            else:
                self._subscribers.clear()


# Global event bus instance
_event_bus = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.

    Returns:
        EventBus: The global event bus
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
