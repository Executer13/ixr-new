"""
Sensor Constants - Centralized constants for sensor operations.

This module contains all hardcoded values related to sensor configuration,
connection parameters, and operational settings.
"""

from enum import Enum


class SensorType(Enum):
    """Enumeration of supported sensor types."""
    MUSE = "Muse"
    MUSE_2 = "Muse 2"
    MUSE_S = "Muse S"
    POLAR_H10 = "Polar H10"


class SensorStatus(Enum):
    """Enumeration of possible sensor statuses."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    STREAMING = "Streaming"
    ERROR = "Error"
    NOT_ALIVE = "Not Alive"


# Muse Sensor Constants
class MuseConstants:
    """Constants specific to Muse sensors."""

    # Connection settings
    CONNECTION_TIMEOUT = 5.0  # seconds
    RECONNECT_INTERVAL = 2.0  # seconds between reconnection attempts

    # Streaming settings
    BUFFER_SIZE = 45000
    CONFIG_P50 = "p50"  # Sets 5th EEG and PPG for Muse 2, 5th EEG for Muse S
    CONFIG_P61 = "p61"  # Sets PPG for Muse S (only works if p50 is set)

    # Sampling rates
    EEG_SAMPLING_RATE = 256.0  # Hz
    PPG_SAMPLING_RATE = 64.0   # Hz
    GYRO_SAMPLING_RATE = 52.0  # Hz

    # Channel information
    EEG_CHANNEL_NAMES = ["TP9", "AF7", "AF8", "TP10", "AUX"]
    PPG_CHANNEL_NAMES = ["PPG1", "PPG2", "PPG3"]
    GYRO_CHANNEL_NAMES = ["Accel_X", "Accel_Y", "Accel_Z", "Gyro_X", "Gyro_Y", "Gyro_Z"]


# Polar Sensor Constants
class PolarConstants:
    """Constants specific to Polar H10 sensor."""

    # BLE UUIDs
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
    BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
    PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
    PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"

    # ECG settings
    ECG_WRITE = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
    ECG_SAMPLING_FREQ = 130  # Hz

    # Connection settings
    CONNECTION_TIMEOUT = 10.0  # seconds
    RECONNECT_INTERVAL = 2.0  # seconds

    # Channel information
    ECG_CHANNEL_NAMES = ["ECG"]
    MANUFACTURER = "Polar"


# General Sensor Settings
class GeneralSensorSettings:
    """General settings applicable to all sensors."""

    AUTO_RECONNECT_ENABLED = True
    STATUS_CHECK_INTERVAL = 1.0  # seconds
    HEALTH_CHECK_TIMEOUT = 5.0   # seconds

    # Thread settings
    DAEMON_THREADS = True
    THREAD_JOIN_TIMEOUT = 2.0  # seconds
