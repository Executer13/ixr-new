"""
Data Transfer Objects for Analysis Services.

These DTOs provide typed data structures for transferring analysis results
between layers of the application.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np


@dataclass
class BandPowerData:
    """
    Brain power data for a specific EEG frequency band.

    Attributes:
        band_name: Name of the frequency band (e.g., "Delta", "Theta", "Alpha")
        frequency_range: Tuple of (low_freq, high_freq) in Hz
        power: Power value for this band
        power_normalized: Normalized power value (0-1 range)
    """
    band_name: str
    frequency_range: tuple  # (low_hz, high_hz)
    power: float
    power_normalized: float = 0.0


@dataclass
class BrainPowerResult:
    """
    Complete brain power analysis result.

    Attributes:
        timestamp: Timestamp when analysis was performed
        final_power: Final brain power metric (0-1)
        short_term_power: Short-term power metric
        long_term_power: Long-term power metric
        band_powers: List of power values for each frequency band
        head_movement: Head movement metric (0-1)
        quality_score: Signal quality score (0-1)
        channel_states: Dict mapping channel names to their state (good/bad)
    """
    timestamp: float
    final_power: float
    short_term_power: float
    long_term_power: float
    band_powers: List[BandPowerData]
    head_movement: float = 0.0
    quality_score: float = 1.0
    channel_states: Optional[Dict[str, str]] = None


@dataclass
class FocusMetrics:
    """
    Focus analysis metrics.

    Attributes:
        timestamp: Timestamp when analysis was performed
        focus_level: Overall focus level (0-1)
        engagement: Engagement metric (0-1)
        workload: Mental workload metric (0-1)
        stress: Stress level metric (0-1)
        relaxation: Relaxation metric (0-1)
    """
    timestamp: float
    focus_level: float
    engagement: float
    workload: float
    stress: float = 0.0
    relaxation: float = 0.0


@dataclass
class AnalysisSettings:
    """
    Configuration settings for analysis.

    Attributes:
        calib_length: Calibration period length in seconds
        power_length: Power calculation window length in seconds
        scale: Scaling factor for power metrics
        offset: Offset for power metrics
        head_impact: Impact factor for head movement (0-1)
        longerterm_length: Long-term averaging window in seconds
        reference: Reference type ("mean", "median", or channel name)
        update_rate: Update frequency in Hz
    """
    calib_length: int = 600  # 10 minutes
    power_length: int = 10  # 10 seconds
    scale: float = 1.5
    offset: float = 0.5
    head_impact: float = 0.2
    longerterm_length: int = 30  # 30 seconds
    reference: str = "mean"
    update_rate: float = 25.0  # 25 Hz

    def to_dict(self) -> Dict:
        """Convert settings to dictionary."""
        return {
            "calib_length": self.calib_length,
            "power_length": self.power_length,
            "scale": self.scale,
            "offset": self.offset,
            "head_impact": self.head_impact,
            "longerterm_length": self.longerterm_length,
            "reference": self.reference,
            "update_rate": self.update_rate
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AnalysisSettings':
        """Create settings from dictionary."""
        return cls(**data)


@dataclass
class StreamData:
    """
    LSL stream data sample.

    Attributes:
        stream_name: Name of the LSL stream
        stream_type: Type of the stream (e.g., "EEG", "Gyro")
        samples: Array of data samples (channels x samples)
        timestamps: Array of timestamps for each sample
        channel_count: Number of channels
        sampling_rate: Nominal sampling rate in Hz
    """
    stream_name: str
    stream_type: str
    samples: np.ndarray
    timestamps: np.ndarray
    channel_count: int
    sampling_rate: float

    @property
    def sample_count(self) -> int:
        """Get the number of samples."""
        return self.samples.shape[1] if len(self.samples.shape) > 1 else len(self.samples)


@dataclass
class SensorData:
    """
    Raw sensor data from hardware.

    Attributes:
        sensor_type: Type of sensor (e.g., "Muse", "Polar H10")
        sensor_id: Unique identifier for the sensor
        data_type: Type of data (e.g., "EEG", "ECG", "Gyro")
        samples: Array of data samples
        timestamps: Array of timestamps
        channel_names: List of channel names
        sampling_rate: Sampling rate in Hz
        metadata: Additional metadata dictionary
    """
    sensor_type: str
    sensor_id: str
    data_type: str
    samples: np.ndarray
    timestamps: np.ndarray
    channel_names: List[str]
    sampling_rate: float
    metadata: Optional[Dict] = None


@dataclass
class AnalysisStatus:
    """
    Status information for an analysis process.

    Attributes:
        is_running: Whether analysis is currently running
        status_message: Human-readable status message
        error: Error message if any
        samples_processed: Number of samples processed
        uptime: Time analysis has been running in seconds
    """
    is_running: bool
    status_message: str
    error: Optional[str] = None
    samples_processed: int = 0
    uptime: float = 0.0
