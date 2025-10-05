# main.py

import sys
import logging
from PyQt5.QtWidgets import QApplication

from gui.dashboard import MainWindow

# Import new architecture components
from src.common.utils.service_container import get_container
from src.common.utils.logger import get_logger, LoggerSetup
from src.common.utils.platform_helper import PlatformInfo, BluetoothHelper
from src.infrastructure.sensors.sensor_factory import SensorFactory
from src.application.services.sensor_service import SensorService
from src.application.services.streaming_service import StreamingService
from src.application.services.analysis_service import AnalysisService
from src.application.services.signal_processor import BrainFlowSignalProcessor


def bootstrap_services():
    """
    Bootstrap and register services in the dependency injection container.

    This sets up the application architecture by registering all services
    in the DI container for later resolution.
    """
    logger = get_logger(__name__)
    logger.info("Bootstrapping services...")

    container = get_container()

    # Register factories
    sensor_factory = SensorFactory()
    container.register_singleton(SensorFactory, sensor_factory)
    logger.debug("Registered SensorFactory")

    # Register services
    sensor_service = SensorService(sensor_factory)
    container.register_singleton(SensorService, sensor_service)
    logger.debug("Registered SensorService")

    streaming_service = StreamingService()
    container.register_singleton(StreamingService, streaming_service)
    logger.debug("Registered StreamingService")

    analysis_service = AnalysisService()
    container.register_singleton(AnalysisService, analysis_service)
    logger.debug("Registered AnalysisService")

    signal_processor = BrainFlowSignalProcessor()
    container.register_singleton(BrainFlowSignalProcessor, signal_processor)
    logger.debug("Registered SignalProcessor")

    logger.info("Services bootstrapped successfully")
    return container


def perform_startup_checks(logger):
    """
    Perform platform-specific startup checks.

    Args:
        logger: Logger instance for reporting checks
    """
    logger.info("Performing platform compatibility checks...")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        logger.error(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        logger.error("Please upgrade Python to continue")
        sys.exit(1)
    else:
        logger.info(f"Python version check passed: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Platform-specific checks
    platform_name = PlatformInfo.get_platform_name()

    if PlatformInfo.is_windows():
        logger.info("Running on Windows - checking compatibility...")
        _check_windows_compatibility(logger)
    elif PlatformInfo.is_mac():
        logger.info("Running on macOS - checking compatibility...")
        _check_mac_compatibility(logger)
    elif PlatformInfo.is_linux():
        logger.info("Running on Linux - checking compatibility...")
        _check_linux_compatibility(logger)
    else:
        logger.warning(f"Unknown platform: {platform_name}")
        logger.warning("Some features may not work as expected")

    logger.info("Startup checks completed")


def _check_windows_compatibility(logger):
    """Windows-specific compatibility checks."""
    # Check Windows version
    try:
        import platform
        win_ver = platform.win32_ver()
        logger.info(f"Windows version: {win_ver[0]}")

        # Recommend Windows 10+
        if win_ver[0] and int(win_ver[0].split('.')[0]) < 10:
            logger.warning("Windows 10 or later is recommended for best compatibility")
    except Exception as e:
        logger.debug(f"Could not detect Windows version: {e}")

    # Check Bluetooth availability
    bt_available, bt_error = BluetoothHelper.check_bluetooth_available()
    if not bt_available:
        logger.warning(f"Bluetooth check: {bt_error}")
        logger.info("Polar H10 sensor will not be available without Bluetooth")


def _check_mac_compatibility(logger):
    """macOS-specific compatibility checks."""
    try:
        import platform
        mac_ver = platform.mac_ver()[0]
        logger.info(f"macOS version: {mac_ver}")

        # Parse version (e.g., "10.15.7")
        if mac_ver:
            major, minor = map(int, mac_ver.split('.')[:2])
            if major == 10 and minor < 13:
                logger.warning("macOS 10.13 (High Sierra) or later is recommended")
                logger.warning("Bluetooth LE features may be limited")
    except Exception as e:
        logger.debug(f"Could not detect macOS version: {e}")

    # Check Bluetooth availability
    bt_available, bt_error = BluetoothHelper.check_bluetooth_available()
    if not bt_available:
        logger.warning(f"Bluetooth check: {bt_error}")
    else:
        logger.info("Remember to grant Bluetooth permissions in System Preferences")


def _check_linux_compatibility(logger):
    """Linux-specific compatibility checks."""
    try:
        import platform
        linux_dist = platform.freedesktop_os_release()
        logger.info(f"Linux distribution: {linux_dist.get('NAME', 'Unknown')}")
        logger.info(f"Version: {linux_dist.get('VERSION', 'Unknown')}")
    except Exception as e:
        logger.debug(f"Could not detect Linux distribution: {e}")

    # Check Bluetooth availability
    bt_available, bt_error = BluetoothHelper.check_bluetooth_available()
    if not bt_available:
        logger.warning(f"Bluetooth check: {bt_error}")
        logger.info("Install bluez: sudo apt-get install bluez")
        logger.info("Add user to bluetooth group: sudo usermod -a -G bluetooth $USER")


def main():
    """
    Main application entry point.

    Sets up logging, bootstraps services, and launches the GUI.
    Includes platform-specific compatibility checks.
    """
    # Setup logging (includes platform diagnostics)
    LoggerSetup.initialize(
        log_level="INFO",
        console_output=True
    )

    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("IXR EEG Suite Starting...")
    logger.info("=" * 60)

    # Perform platform-specific startup checks
    perform_startup_checks(logger)

    try:
        # Bootstrap services (DI container)
        container = bootstrap_services()
        logger.info("Service container initialized")

        # Create Qt application
        app = QApplication(sys.argv)
        logger.info("Qt application created")

        # Create and show main window
        window = MainWindow()
        window.show()
        logger.info("Main window displayed")

        # Start event loop
        logger.info("Starting Qt event loop...")
        exit_code = app.exec_()

        logger.info(f"Application exiting with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
