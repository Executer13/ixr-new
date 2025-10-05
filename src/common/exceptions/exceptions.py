"""
Custom Exceptions - Application-specific exception hierarchy.

This module defines custom exceptions for better error handling
and debugging throughout the application.
"""


class IXRException(Exception):
    """Base exception for all IXR Suite exceptions."""
    pass


# Sensor-related exceptions
class SensorException(IXRException):
    """Base exception for sensor-related errors."""
    pass


class SensorConnectionError(SensorException):
    """Raised when sensor connection fails."""
    pass


class SensorNotConnectedError(SensorException):
    """Raised when attempting operations on disconnected sensor."""
    pass


class SensorStreamingError(SensorException):
    """Raised when sensor streaming encounters an error."""
    pass


class SensorConfigurationError(SensorException):
    """Raised when sensor configuration is invalid."""
    pass


# Streaming-related exceptions
class StreamingException(IXRException):
    """Base exception for streaming-related errors."""
    pass


class StreamNotFoundException(StreamingException):
    """Raised when a requested stream cannot be found."""
    pass


class StreamCreationError(StreamingException):
    """Raised when stream creation fails."""
    pass


class StreamPublishError(StreamingException):
    """Raised when data publishing fails."""
    pass


# Analysis-related exceptions
class AnalysisException(IXRException):
    """Base exception for analysis-related errors."""
    pass


class AnalysisNotRunningError(AnalysisException):
    """Raised when attempting to access analysis that's not running."""
    pass


class AnalysisConfigurationError(AnalysisException):
    """Raised when analysis configuration is invalid."""
    pass


class InsufficientDataError(AnalysisException):
    """Raised when there's insufficient data for analysis."""
    pass


# Signal processing exceptions
class SignalProcessingException(IXRException):
    """Base exception for signal processing errors."""
    pass


class InvalidFilterParametersError(SignalProcessingException):
    """Raised when filter parameters are invalid."""
    pass


class InvalidSignalError(SignalProcessingException):
    """Raised when signal data is invalid."""
    pass


# Configuration exceptions
class ConfigurationException(IXRException):
    """Base exception for configuration-related errors."""
    pass


class ConfigurationLoadError(ConfigurationException):
    """Raised when configuration loading fails."""
    pass


class ConfigurationSaveError(ConfigurationException):
    """Raised when configuration saving fails."""
    pass


# UI exceptions
class UIException(IXRException):
    """Base exception for UI-related errors."""
    pass


class WidgetInitializationError(UIException):
    """Raised when widget initialization fails."""
    pass
