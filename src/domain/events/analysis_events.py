"""
Analysis Events - Domain events for analysis operations.

This module defines all events related to analysis operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
from .event_bus import Event


class AnalysisEventTypes:
    """Event type constants for analysis events."""
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_STOPPED = "analysis.stopped"
    ANALYSIS_UPDATED = "analysis.updated"
    ANALYSIS_ERROR = "analysis.error"
    CALIBRATION_STARTED = "analysis.calibration.started"
    CALIBRATION_COMPLETED = "analysis.calibration.completed"


@dataclass
class AnalysisStartedEvent(Event):
    """Event emitted when analysis starts."""

    def __init__(self, analysis_type: str, settings: Dict[str, Any]):
        super().__init__(
            timestamp=datetime.now(),
            event_type=AnalysisEventTypes.ANALYSIS_STARTED,
            source="analysis_service",
            data={
                "analysis_type": analysis_type,
                "settings": settings
            }
        )


@dataclass
class AnalysisStoppedEvent(Event):
    """Event emitted when analysis stops."""

    def __init__(self, analysis_type: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=AnalysisEventTypes.ANALYSIS_STOPPED,
            source="analysis_service",
            data={
                "analysis_type": analysis_type
            }
        )


@dataclass
class AnalysisUpdatedEvent(Event):
    """Event emitted when analysis results are updated."""

    def __init__(self, analysis_type: str, results: Dict[str, Any]):
        super().__init__(
            timestamp=datetime.now(),
            event_type=AnalysisEventTypes.ANALYSIS_UPDATED,
            source="analysis_service",
            data={
                "analysis_type": analysis_type,
                "results": results
            }
        )


@dataclass
class AnalysisErrorEvent(Event):
    """Event emitted when an analysis error occurs."""

    def __init__(self, analysis_type: str, error: str):
        super().__init__(
            timestamp=datetime.now(),
            event_type=AnalysisEventTypes.ANALYSIS_ERROR,
            source="analysis_service",
            data={
                "analysis_type": analysis_type,
                "error": error
            }
        )
