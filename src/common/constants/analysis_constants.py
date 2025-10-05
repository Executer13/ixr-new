"""
Analysis Constants - Centralized constants for analysis operations.

This module contains all hardcoded values related to brain power analysis,
focus analysis, and other analytical operations.
"""


class BrainPowerDefaults:
    """Default settings for brain power analysis."""

    # Calibration settings
    CALIBRATION_LENGTH = 600    # seconds (10 minutes)
    POWER_LENGTH = 10           # seconds

    # Scaling and offset
    SCALE = 1.5
    OFFSET = 0.5

    # Impact settings
    HEAD_IMPACT = 0.2
    LONGERTERM_LENGTH = 30      # seconds

    # Reference method
    REFERENCE = "mean"          # "mean" or "median"

    # Metric names
    METRIC_NAMES = ["Short-term", "Long-term", "Final"]

    # Plot settings
    METRICS_PLOT_X_RANGE = (0.1, 3.9)
    METRICS_PLOT_Y_RANGE = (-0.1, 1.1)

    BANDS_PLOT_X_RANGE = (0.1, 5.9)
    BANDS_PLOT_Y_RANGE = (-0.1, 50)

    # Bar chart settings
    BAR_WIDTH = 0.8
    INITIAL_BAR_HEIGHT = 0.1  # Small initial value so bars are visible


class FocusAnalysisDefaults:
    """Default settings for focus analysis."""

    # Window settings
    ANALYSIS_WINDOW = 5.0       # seconds
    UPDATE_INTERVAL = 1.0       # seconds

    # Thresholds
    FOCUS_THRESHOLD = 0.6       # 60% focus threshold
    DISTRACTION_THRESHOLD = 0.4 # 40% distraction threshold

    # Moving average
    MOVING_AVERAGE_WINDOW = 10  # samples


class AnalysisDefaults:
    """Default settings for general analysis service."""

    DEFAULT_SETTINGS = {
        "analysis_type": "brain_power",
        "calib_length": BrainPowerDefaults.CALIBRATION_LENGTH,
        "power_length": BrainPowerDefaults.POWER_LENGTH,
        "scale": BrainPowerDefaults.SCALE,
        "reference": BrainPowerDefaults.REFERENCE,
    }


class AnalysisStatus:
    """Status messages for analysis operations."""

    NOT_RUNNING = "Not running"
    STARTING = "Starting analysis..."
    RUNNING = "Running"
    CALIBRATING = "Calibrating..."
    STOPPING = "Stopping..."
    ERROR = "ERROR"

    NO_BOARD_CONNECTED = "No Board Connected"
    BOARD_NOT_READY = "Board Not Ready"
    ANALYSIS_RUNNING = "Analysis Running"
