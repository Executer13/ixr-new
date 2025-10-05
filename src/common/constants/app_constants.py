"""
Application Constants - General application-level constants.

This module contains constants used across the entire application.
"""


class AppInfo:
    """Application information."""

    NAME = "IXR Labs Suite"
    VERSION = "2.0.0"
    ORGANIZATION = "IXR Labs"

    # Window settings
    DEFAULT_WIDTH = 1400
    DEFAULT_HEIGHT = 1200
    DEFAULT_X = 100
    DEFAULT_Y = 100


class TabNames:
    """Names of application tabs."""

    SENSORS = "Sensors"
    PLOT = "Plot"
    ANALYSIS = "Analysis"


class LSLDefaults:
    """LSL stream defaults."""

    SOURCE_ID = "ixr-suite-lsl-data-publisher"
    RESOLVE_TIMEOUT = 1.0  # seconds

    # Stream name prefixes
    STREAM_PREFIX_EEG = "ixr-suite-eeg-data"
    STREAM_PREFIX_GYRO = "ixr-suite-gyro-data"
    STREAM_PREFIX_PPG = "ixr-suite-ppg-data"


class ThreadSettings:
    """Thread configuration settings."""

    DAEMON_DEFAULT = True
    JOIN_TIMEOUT = 2.0  # seconds

    # Thread names
    SENSOR_STATUS_THREAD = "sensor_status_checker"
    LSL_PUBLISHER_THREAD = "lsl_data_pusher"
    BLE_EVENT_LOOP_THREAD = "ble_event_loop"
    ANALYSIS_WORKER_THREAD = "analysis_worker"


class LogSettings:
    """Logging configuration."""

    # Log levels
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    # Log format
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # File settings
    LOG_FILE = "ixr_suite.log"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5


class UIConstants:
    """UI-related constants."""

    # Spacing
    DEFAULT_MARGIN = 24
    DEFAULT_SPACING = 20
    COMPACT_SPACING = 12
    TIGHT_SPACING = 8

    # Border radius
    CARD_RADIUS = 12
    BUTTON_RADIUS = 8
    INPUT_RADIUS = 8

    # Font sizes
    TITLE_SIZE = 20
    SUBTITLE_SIZE = 18
    BODY_SIZE = 13
    SMALL_SIZE = 12

    # Widget dimensions
    BUTTON_PADDING = "10px 20px"
    INPUT_PADDING = "8px 12px"

    # Indicator settings
    INDICATOR_SIZE = 14
    INDICATOR_BLUR_RADIUS = 16
    INDICATOR_MARGIN = 10
