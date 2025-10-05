"""
Analysis Service Interface - Defines the contract for analysis services.

This interface ensures consistent analysis functionality across different
analysis implementations.
"""

from abc import ABC, ABCMeta, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np
from PyQt5.QtCore import QObject


# Create a compatible metaclass that combines QObject and ABC
class QABCMeta(type(QObject), ABCMeta):
    """Metaclass that combines Qt's metaclass with ABC's metaclass."""
    pass


class IAnalysisService(QObject, metaclass=QABCMeta):
    """
    Abstract base class for analysis service implementations.

    Analysis services are responsible for:
    - Processing EEG/sensor data
    - Computing metrics and features
    - Providing real-time analysis results
    - Managing analysis configuration
    """

    @abstractmethod
    def start_analysis(self, settings: Dict) -> None:
        """
        Start the analysis process with given settings.

        Args:
            settings: Dictionary containing analysis configuration

        Raises:
            RuntimeError: If analysis cannot be started
        """
        pass

    @abstractmethod
    def stop_analysis(self) -> None:
        """
        Stop the analysis process.
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if analysis is currently running.

        Returns:
            bool: True if analysis is running, False otherwise
        """
        pass

    @abstractmethod
    def get_settings(self) -> Dict:
        """
        Get the current analysis settings.

        Returns:
            Dict: Current analysis configuration
        """
        pass

    @abstractmethod
    def update_settings(self, settings: Dict) -> None:
        """
        Update analysis settings.

        Args:
            settings: New analysis configuration

        Raises:
            ValueError: If settings are invalid
        """
        pass


class ISignalProcessor(ABC):
    """
    Abstract base class for signal processing implementations.

    Signal processors are responsible for:
    - Filtering signals
    - Computing spectral features
    - Detrending and preprocessing
    """

    @abstractmethod
    def apply_bandpass_filter(self, data: np.ndarray,
                              sampling_rate: float,
                              low_freq: float,
                              high_freq: float) -> np.ndarray:
        """
        Apply bandpass filter to the signal.

        Args:
            data: Input signal data
            sampling_rate: Sampling rate of the signal in Hz
            low_freq: Lower cutoff frequency in Hz
            high_freq: Upper cutoff frequency in Hz

        Returns:
            Filtered signal data
        """
        pass

    @abstractmethod
    def apply_notch_filter(self, data: np.ndarray,
                          sampling_rate: float,
                          notch_freq: float) -> np.ndarray:
        """
        Apply notch filter to remove line noise.

        Args:
            data: Input signal data
            sampling_rate: Sampling rate of the signal in Hz
            notch_freq: Frequency to notch out (e.g., 50Hz or 60Hz)

        Returns:
            Filtered signal data
        """
        pass

    @abstractmethod
    def compute_psd(self, data: np.ndarray,
                   sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Power Spectral Density using Welch's method.

        Args:
            data: Input signal data
            sampling_rate: Sampling rate of the signal in Hz

        Returns:
            Tuple of (frequencies, power_values)
        """
        pass

    @abstractmethod
    def compute_band_power(self, psd_data: Tuple[np.ndarray, np.ndarray],
                          band_range: Tuple[float, float]) -> float:
        """
        Compute power in a specific frequency band.

        Args:
            psd_data: Tuple of (frequencies, power_values) from compute_psd
            band_range: Tuple of (low_freq, high_freq) defining the band

        Returns:
            Power in the specified frequency band
        """
        pass

    @abstractmethod
    def detrend(self, data: np.ndarray) -> np.ndarray:
        """
        Remove linear trend from the signal.

        Args:
            data: Input signal data

        Returns:
            Detrended signal data
        """
        pass
