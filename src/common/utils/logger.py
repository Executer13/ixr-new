"""
Logging Utility - Centralized logging configuration and helpers.

This module provides a consistent logging interface across the application,
replacing print statements with proper logging.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.common.constants.app_constants import LogSettings


class LoggerSetup:
    """
    Centralized logger configuration.

    Provides methods to setup and configure loggers with consistent formatting,
    file rotation, and console output.
    """

    _initialized = False
    _log_file_path: Optional[Path] = None

    @classmethod
    def initialize(cls, log_file: Optional[str] = None,
                  log_level: str = LogSettings.INFO,
                  console_output: bool = True) -> None:
        """
        Initialize the logging system.

        Args:
            log_file: Path to log file. If None, uses default from LogSettings
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to also output to console
        """
        if cls._initialized:
            return

        # Determine log file path
        if log_file:
            cls._log_file_path = Path(log_file)
        else:
            # Store logs in user's home directory
            home = Path.home()
            log_dir = home / ".ixr_suite" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            cls._log_file_path = log_dir / LogSettings.LOG_FILE

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))

        # Remove existing handlers
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            LogSettings.FORMAT,
            datefmt=LogSettings.DATE_FORMAT
        )

        # File handler with rotation
        file_handler = RotatingFileHandler(
            cls._log_file_path,
            maxBytes=LogSettings.MAX_LOG_SIZE,
            backupCount=LogSettings.BACKUP_COUNT
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Console handler (if enabled)
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        cls._initialized = True

        # Log initialization with platform diagnostics
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("Logging system initialized")
        logger.info(f"Log file: {cls._log_file_path}")
        logger.info(f"Log level: {log_level}")

        # Log platform information for diagnostics
        cls._log_platform_info(logger)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: Name of the logger (typically __name__)

        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._initialized:
            cls.initialize()

        return logging.getLogger(name)

    @classmethod
    def set_level(cls, log_level: str) -> None:
        """
        Change the logging level for all handlers.

        Args:
            log_level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level = getattr(logging, log_level)
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        for handler in root_logger.handlers:
            handler.setLevel(level)

    @classmethod
    def get_log_file_path(cls) -> Optional[Path]:
        """
        Get the path to the log file.

        Returns:
            Path: Path to log file, or None if not initialized
        """
        return cls._log_file_path

    @classmethod
    def _log_platform_info(cls, logger: logging.Logger) -> None:
        """
        Log comprehensive platform diagnostic information.

        Args:
            logger: Logger instance to use
        """
        try:
            # Import here to avoid circular dependency
            from src.common.utils.platform_helper import get_diagnostic_info
            import sys

            logger.info("-" * 60)
            logger.info("PLATFORM DIAGNOSTICS")
            logger.info("-" * 60)

            # Get diagnostic info
            diag = get_diagnostic_info()

            logger.info(f"Platform: {diag['platform']}")
            logger.info(f"Platform Details: {diag['platform_details']}")
            logger.info(f"Python Version: {sys.version.split()[0]}")
            logger.info(f"Architecture: {diag['architecture']}")
            logger.info(f"Bluetooth Available: {diag['bluetooth_available']}")
            if diag['bluetooth_error']:
                logger.warning(f"Bluetooth Error: {diag['bluetooth_error']}")
            logger.info(f"App Data Directory: {diag['app_data_dir']}")
            logger.info(f"Log Directory: {diag['log_dir']}")

            # Log key library versions
            cls._log_library_versions(logger)

            logger.info("-" * 60)
        except Exception as e:
            logger.warning(f"Could not log platform diagnostics: {e}")

    @classmethod
    def _log_library_versions(cls, logger: logging.Logger) -> None:
        """
        Log versions of key libraries.

        Args:
            logger: Logger instance to use
        """
        libraries = [
            ('brainflow', 'BrainFlow'),
            ('pylsl', 'Lab Streaming Layer'),
            ('PyQt5', 'PyQt5'),
            ('pyqtgraph', 'PyQtGraph'),
            ('numpy', 'NumPy'),
            ('scipy', 'SciPy'),
            ('bleak', 'Bleak')
        ]

        logger.info("Key Library Versions:")
        for module_name, display_name in libraries:
            try:
                module = __import__(module_name)
                version = getattr(module, '__version__', 'unknown')
                logger.info(f"  {display_name}: {version}")
            except ImportError:
                logger.info(f"  {display_name}: not installed")
            except Exception as e:
                logger.debug(f"  {display_name}: error getting version ({e})")


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return LoggerSetup.get_logger(name)


# Convenience functions for common logging patterns
def log_sensor_event(logger: logging.Logger, sensor_type: str,
                    event: str, level: str = "INFO") -> None:
    """
    Log a sensor event with consistent formatting.

    Args:
        logger: Logger instance
        sensor_type: Type of sensor (e.g., "Muse", "Polar")
        event: Event description
        level: Log level
    """
    log_func = getattr(logger, level.lower())
    log_func(f"[{sensor_type}] {event}")


def log_stream_event(logger: logging.Logger, stream_name: str,
                    event: str, level: str = "INFO") -> None:
    """
    Log a stream event with consistent formatting.

    Args:
        logger: Logger instance
        stream_name: Name of the stream
        event: Event description
        level: Log level
    """
    log_func = getattr(logger, level.lower())
    log_func(f"[Stream: {stream_name}] {event}")


def log_analysis_event(logger: logging.Logger, analysis_type: str,
                      event: str, level: str = "INFO") -> None:
    """
    Log an analysis event with consistent formatting.

    Args:
        logger: Logger instance
        analysis_type: Type of analysis
        event: Event description
        level: Log level
    """
    log_func = getattr(logger, level.lower())
    log_func(f"[Analysis: {analysis_type}] {event}")
