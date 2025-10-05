"""
Analysis Service - Manages brain power and focus analysis operations.

This service provides high-level API for managing analysis workflows,
coordinating data processing, and publishing analysis results.
"""

from typing import Dict, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import logging

from src.domain.interfaces.i_analysis_service import IAnalysisService
from src.domain.events.event_bus import get_event_bus
from src.domain.events.analysis_events import (
    AnalysisStartedEvent,
    AnalysisStoppedEvent,
    AnalysisUpdatedEvent,
    AnalysisErrorEvent
)
from src.common.constants.analysis_constants import AnalysisDefaults
from src.common.exceptions.exceptions import (
    AnalysisException,
    AnalysisNotRunningError,
    InsufficientDataError
)
from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisService(IAnalysisService):
    """
    Service for managing analysis operations.

    Responsibilities:
    - Manage analysis lifecycle (start, stop, update)
    - Coordinate with signal processors
    - Track analysis state and settings
    - Publish analysis events
    - Handle analysis errors

    Signals:
        analysis_updated: Emitted when new analysis results are available
        analysis_started: Emitted when analysis begins
        analysis_stopped: Emitted when analysis ends
        status_updated: Emitted when status changes
    """

    analysis_updated = pyqtSignal(dict)  # Analysis results
    analysis_started = pyqtSignal()
    analysis_stopped = pyqtSignal()
    status_updated = pyqtSignal(str)  # Status message

    def __init__(self):
        """Initialize the analysis service."""
        super().__init__()
        self._is_running = False
        self._settings = AnalysisDefaults.DEFAULT_SETTINGS.copy()
        self._worker = None
        self._worker_thread = None
        self._event_bus = get_event_bus()
        logger.info("AnalysisService initialized")

    def start_analysis(self, settings: Optional[Dict] = None) -> None:
        """
        Start the analysis process with given settings.

        Args:
            settings: Optional dictionary containing analysis configuration.
                     If None, uses default settings.

        Raises:
            AnalysisException: If analysis cannot be started
        """
        if self._is_running:
            logger.warning("Analysis already running")
            return

        try:
            # Update settings if provided
            if settings:
                self._settings.update(settings)

            logger.info(f"Starting analysis with settings: {self._settings}")

            # Mark as running
            self._is_running = True

            # Emit signals
            self.analysis_started.emit()
            self.status_updated.emit("Analysis started")

            # Publish event
            event = AnalysisStartedEvent(self._settings.get("analysis_type", "brain_power"))
            self._event_bus.publish(event)

            logger.info("Analysis started successfully")

        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start analysis: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Publish error event
            error_event = AnalysisErrorEvent(
                analysis_type=self._settings.get("analysis_type", "unknown"),
                error=error_msg
            )
            self._event_bus.publish(error_event)

            raise AnalysisException(error_msg)

    def stop_analysis(self) -> None:
        """
        Stop the analysis process.

        Raises:
            AnalysisNotRunningError: If analysis is not running
        """
        if not self._is_running:
            logger.warning("Analysis not running")
            return

        try:
            logger.info("Stopping analysis")

            # Stop worker thread if exists
            if self._worker_thread and self._worker_thread.isRunning():
                if self._worker:
                    self._worker.stop()
                self._worker_thread.quit()
                self._worker_thread.wait()

            # Mark as stopped
            self._is_running = False

            # Emit signals
            self.analysis_stopped.emit()
            self.status_updated.emit("Analysis stopped")

            # Publish event
            event = AnalysisStoppedEvent(self._settings.get("analysis_type", "brain_power"))
            self._event_bus.publish(event)

            logger.info("Analysis stopped successfully")

        except Exception as e:
            error_msg = f"Error stopping analysis: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise AnalysisException(error_msg)

    def is_running(self) -> bool:
        """
        Check if analysis is currently running.

        Returns:
            bool: True if analysis is running, False otherwise
        """
        return self._is_running

    def get_settings(self) -> Dict:
        """
        Get the current analysis settings.

        Returns:
            Dict: Current analysis configuration
        """
        return self._settings.copy()

    def update_settings(self, settings: Dict) -> None:
        """
        Update analysis settings.

        Args:
            settings: New analysis configuration

        Raises:
            ValueError: If settings are invalid
        """
        try:
            # Validate settings
            self._validate_settings(settings)

            # Update settings
            old_settings = self._settings.copy()
            self._settings.update(settings)

            logger.info(f"Updated analysis settings: {settings}")

            # If analysis is running, emit update event
            if self._is_running:
                event = AnalysisUpdatedEvent(
                    analysis_type=self._settings.get("analysis_type", "brain_power"),
                    metrics={"settings_changed": True}
                )
                self._event_bus.publish(event)

                self.status_updated.emit("Settings updated")

        except ValueError as e:
            logger.error(f"Invalid settings: {e}")
            raise
        except Exception as e:
            error_msg = f"Failed to update settings: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise AnalysisException(error_msg)

    def publish_analysis_results(self, results: Dict[str, Any]) -> None:
        """
        Publish analysis results.

        Args:
            results: Dictionary containing analysis results
        """
        try:
            # Emit signal with results
            self.analysis_updated.emit(results)

            # Publish event
            event = AnalysisUpdatedEvent(
                analysis_type=self._settings.get("analysis_type", "brain_power"),
                metrics=results
            )
            self._event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing analysis results: {e}")

    def set_worker(self, worker: QObject, thread: QThread) -> None:
        """
        Set the worker and thread for analysis.

        Args:
            worker: Worker object that performs analysis
            thread: QThread that runs the worker
        """
        self._worker = worker
        self._worker_thread = thread

        # Connect worker signals
        if hasattr(worker, 'analysisUpdated'):
            worker.analysisUpdated.connect(self.publish_analysis_results)
        if hasattr(worker, 'statusUpdated'):
            worker.statusUpdated.connect(lambda msg: self.status_updated.emit(msg))

        logger.debug("Worker and thread set for analysis service")

    def get_worker(self) -> Optional[QObject]:
        """
        Get the current worker object.

        Returns:
            Optional[QObject]: Worker object if set, None otherwise
        """
        return self._worker

    def _validate_settings(self, settings: Dict) -> None:
        """
        Validate analysis settings.

        Args:
            settings: Settings to validate

        Raises:
            ValueError: If settings are invalid
        """
        # Validate required fields if present
        if "calib_length" in settings:
            if not isinstance(settings["calib_length"], (int, float)) or settings["calib_length"] <= 0:
                raise ValueError("calib_length must be a positive number")

        if "power_length" in settings:
            if not isinstance(settings["power_length"], (int, float)) or settings["power_length"] <= 0:
                raise ValueError("power_length must be a positive number")

        if "scale" in settings:
            if not isinstance(settings["scale"], (int, float)) or settings["scale"] <= 0:
                raise ValueError("scale must be a positive number")

        if "reference" in settings:
            valid_refs = ["mean", "median", "none"]
            if settings["reference"] not in valid_refs:
                raise ValueError(f"reference must be one of {valid_refs}")

    def cleanup(self) -> None:
        """Cleanup the service and stop any running analysis."""
        logger.info("Cleaning up AnalysisService")

        if self._is_running:
            self.stop_analysis()

        self._worker = None
        self._worker_thread = None

        logger.info("AnalysisService cleanup complete")
