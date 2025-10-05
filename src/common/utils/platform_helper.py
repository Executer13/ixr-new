"""
Platform Helper - Cross-platform compatibility utilities.

This module provides utilities for detecting the current platform
and handling platform-specific operations.
"""

import sys
import platform
from pathlib import Path
from typing import Tuple, Optional
import subprocess


class PlatformInfo:
    """
    Platform detection and information utilities.

    Provides methods to detect the current operating system and
    retrieve platform-specific information.
    """

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return sys.platform == 'win32'

    @staticmethod
    def is_mac() -> bool:
        """Check if running on macOS."""
        return sys.platform == 'darwin'

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return sys.platform.startswith('linux')

    @staticmethod
    def get_platform_name() -> str:
        """
        Get human-readable platform name.

        Returns:
            str: "Windows", "macOS", "Linux", or "Unknown"
        """
        if PlatformInfo.is_windows():
            return "Windows"
        elif PlatformInfo.is_mac():
            return "macOS"
        elif PlatformInfo.is_linux():
            return "Linux"
        else:
            return "Unknown"

    @staticmethod
    def get_platform_details() -> str:
        """
        Get detailed platform information.

        Returns:
            str: Detailed platform description
        """
        return platform.platform()

    @staticmethod
    def get_python_version() -> str:
        """Get Python version string."""
        return sys.version

    @staticmethod
    def get_architecture() -> str:
        """Get system architecture (e.g., 'x86_64', 'arm64')."""
        return platform.machine()


class BluetoothHelper:
    """
    Platform-specific Bluetooth/BLE helpers.

    Provides utilities to check Bluetooth capabilities and permissions
    on different platforms.
    """

    @staticmethod
    def check_bluetooth_available() -> Tuple[bool, Optional[str]]:
        """
        Check if Bluetooth is available on the system.

        Returns:
            Tuple[bool, Optional[str]]: (is_available, error_message)
        """
        if PlatformInfo.is_windows():
            return BluetoothHelper._check_windows_bluetooth()
        elif PlatformInfo.is_mac():
            return BluetoothHelper._check_mac_bluetooth()
        elif PlatformInfo.is_linux():
            return BluetoothHelper._check_linux_bluetooth()
        else:
            return False, "Unsupported platform"

    @staticmethod
    def _check_windows_bluetooth() -> Tuple[bool, Optional[str]]:
        """Check Bluetooth on Windows."""
        try:
            # On Windows, bleak will handle BLE adapter detection
            # We can assume it's available if the import works
            import bleak
            return True, None
        except ImportError:
            return False, "bleak library not installed"
        except Exception as e:
            return False, f"Error checking Bluetooth: {str(e)}"

    @staticmethod
    def _check_mac_bluetooth() -> Tuple[bool, Optional[str]]:
        """Check Bluetooth on macOS."""
        try:
            # On macOS, check if Bluetooth is enabled via system_profiler
            result = subprocess.run(
                ['system_profiler', 'SPBluetoothDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, "Bluetooth may not be available"
        except FileNotFoundError:
            # system_profiler not found (unlikely on macOS)
            return True, None  # Assume available
        except subprocess.TimeoutExpired:
            return True, None  # Assume available
        except Exception as e:
            return True, None  # Assume available, log error later

    @staticmethod
    def _check_linux_bluetooth() -> Tuple[bool, Optional[str]]:
        """Check Bluetooth on Linux."""
        try:
            # Check if bluetoothctl is available
            result = subprocess.run(
                ['bluetoothctl', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, "bluetoothctl not found"
        except FileNotFoundError:
            return False, "bluetoothctl not installed (install bluez)"
        except subprocess.TimeoutExpired:
            return False, "Bluetooth check timed out"
        except Exception as e:
            return False, f"Error checking Bluetooth: {str(e)}"

    @staticmethod
    def get_bluetooth_help_message() -> str:
        """
        Get platform-specific help message for Bluetooth issues.

        Returns:
            str: Help message for enabling/troubleshooting Bluetooth
        """
        if PlatformInfo.is_windows():
            return (
                "Windows Bluetooth Help:\n"
                "1. Ensure Bluetooth is enabled in Windows Settings\n"
                "2. Check that Bluetooth drivers are installed\n"
                "3. Try running the application as Administrator\n"
                "4. Some Bluetooth adapters may not support BLE"
            )
        elif PlatformInfo.is_mac():
            return (
                "macOS Bluetooth Help:\n"
                "1. Enable Bluetooth in System Preferences\n"
                "2. Grant Bluetooth permissions to the application:\n"
                "   System Preferences > Security & Privacy > Bluetooth\n"
                "3. Ensure you're running macOS 10.13 or later\n"
                "4. Try restarting Bluetooth module"
            )
        elif PlatformInfo.is_linux():
            return (
                "Linux Bluetooth Help:\n"
                "1. Install bluez: sudo apt-get install bluez\n"
                "2. Enable Bluetooth service: sudo systemctl enable bluetooth\n"
                "3. Start Bluetooth service: sudo systemctl start bluetooth\n"
                "4. Add user to bluetooth group: sudo usermod -a -G bluetooth $USER"
            )
        else:
            return "Bluetooth troubleshooting not available for this platform"


class PathHelper:
    """
    Platform-specific path utilities.

    Provides helpers for creating platform-appropriate file paths.
    """

    @staticmethod
    def get_app_data_dir() -> Path:
        """
        Get platform-appropriate application data directory.

        Returns:
            Path: Application data directory
        """
        home = Path.home()

        if PlatformInfo.is_windows():
            # Use AppData/Local on Windows
            app_data = Path(os.environ.get('LOCALAPPDATA', home / 'AppData' / 'Local'))
            return app_data / 'IXR_Suite'
        elif PlatformInfo.is_mac():
            # Use ~/Library/Application Support on macOS
            return home / 'Library' / 'Application Support' / 'IXR_Suite'
        else:
            # Use ~/.config on Linux (XDG spec)
            config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
            return config_home / 'ixr_suite'

    @staticmethod
    def get_log_dir() -> Path:
        """
        Get platform-appropriate log directory.

        Returns:
            Path: Log directory
        """
        if PlatformInfo.is_windows():
            # Logs in AppData/Local/IXR_Suite/logs
            return PathHelper.get_app_data_dir() / 'logs'
        elif PlatformInfo.is_mac():
            # Logs in ~/Library/Logs/IXR_Suite
            return Path.home() / 'Library' / 'Logs' / 'IXR_Suite'
        else:
            # Logs in ~/.local/share/ixr_suite/logs (XDG spec)
            data_home = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
            return data_home / 'ixr_suite' / 'logs'

    @staticmethod
    def ensure_dir_exists(path: Path) -> Path:
        """
        Ensure directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure

        Returns:
            Path: The ensured directory path
        """
        path.mkdir(parents=True, exist_ok=True)
        return path


# Import os for PathHelper
import os


def get_diagnostic_info() -> dict:
    """
    Get comprehensive diagnostic information about the platform.

    Returns:
        dict: Dictionary containing diagnostic information
    """
    bluetooth_available, bluetooth_error = BluetoothHelper.check_bluetooth_available()

    return {
        'platform': PlatformInfo.get_platform_name(),
        'platform_details': PlatformInfo.get_platform_details(),
        'python_version': PlatformInfo.get_python_version(),
        'architecture': PlatformInfo.get_architecture(),
        'bluetooth_available': bluetooth_available,
        'bluetooth_error': bluetooth_error,
        'app_data_dir': str(PathHelper.get_app_data_dir()),
        'log_dir': str(PathHelper.get_log_dir())
    }
