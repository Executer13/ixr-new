"""
Signal Processor - Implementation of signal processing operations.

This module provides concrete implementations for filtering, spectral analysis,
and preprocessing of EEG/biosignal data using BrainFlow and SciPy.
"""

from typing import Tuple, Optional
import numpy as np
from scipy.signal import butter, filtfilt, welch
from brainflow import DataFilter, DetrendOperations, FilterTypes, WindowOperations

from src.domain.interfaces.i_analysis_service import ISignalProcessor
from src.common.constants.plot_constants import SignalProcessing, EEGBands
from src.common.exceptions.exceptions import (
    SignalProcessingException,
    InvalidFilterParametersError
)
from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class BrainFlowSignalProcessor(ISignalProcessor):
    """
    Signal processor implementation using BrainFlow and SciPy.

    This processor provides:
    - Bandpass and notch filtering using BrainFlow
    - Power Spectral Density computation using Welch's method
    - EEG band power calculations
    - Detrending and preprocessing
    """

    def __init__(self):
        """Initialize the signal processor."""
        logger.info("BrainFlowSignalProcessor initialized")

    def apply_bandpass_filter(
        self,
        data: np.ndarray,
        sampling_rate: float,
        low_freq: float,
        high_freq: float,
        order: int = 2
    ) -> np.ndarray:
        """
        Apply bandpass filter to the signal using BrainFlow.

        Args:
            data: Input signal data (1D array)
            sampling_rate: Sampling rate of the signal in Hz
            low_freq: Lower cutoff frequency in Hz
            high_freq: Upper cutoff frequency in Hz
            order: Filter order (default: 2)

        Returns:
            Filtered signal data

        Raises:
            InvalidFilterParametersError: If filter parameters are invalid
            SignalProcessingException: If filtering fails
        """
        try:
            # Validate parameters
            if low_freq <= 0 or high_freq <= 0:
                raise InvalidFilterParametersError("Frequencies must be positive")

            if low_freq >= high_freq:
                raise InvalidFilterParametersError(
                    f"Low frequency ({low_freq}) must be less than high frequency ({high_freq})"
                )

            if high_freq >= sampling_rate / 2:
                raise InvalidFilterParametersError(
                    f"High frequency ({high_freq}) must be less than Nyquist frequency ({sampling_rate/2})"
                )

            # Make a copy to avoid modifying original data
            filtered_data = data.copy()

            # Apply bandpass filter using BrainFlow
            DataFilter.perform_bandpass(
                data=filtered_data,
                sampling_rate=int(sampling_rate),
                start_freq=low_freq,
                stop_freq=high_freq,
                order=order,
                filter_type=FilterTypes.BUTTERWORTH.value,
                ripple=0.0
            )

            logger.debug(f"Applied bandpass filter: {low_freq}-{high_freq} Hz @ {sampling_rate} Hz")
            return filtered_data

        except InvalidFilterParametersError:
            raise
        except Exception as e:
            error_msg = f"Bandpass filtering failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def apply_notch_filter(
        self,
        data: np.ndarray,
        sampling_rate: float,
        notch_freq: float,
        bandwidth: float = 4.0,
        order: int = 2
    ) -> np.ndarray:
        """
        Apply notch filter to remove line noise using BrainFlow bandstop.

        Args:
            data: Input signal data (1D array)
            sampling_rate: Sampling rate of the signal in Hz
            notch_freq: Frequency to notch out (e.g., 50Hz or 60Hz)
            bandwidth: Bandwidth of the notch in Hz (default: 4.0)
            order: Filter order (default: 2)

        Returns:
            Filtered signal data

        Raises:
            InvalidFilterParametersError: If filter parameters are invalid
            SignalProcessingException: If filtering fails
        """
        try:
            # Validate parameters
            if notch_freq <= 0:
                raise InvalidFilterParametersError("Notch frequency must be positive")

            if notch_freq >= sampling_rate / 2:
                raise InvalidFilterParametersError(
                    f"Notch frequency ({notch_freq}) must be less than Nyquist frequency ({sampling_rate/2})"
                )

            # Make a copy to avoid modifying original data
            filtered_data = data.copy()

            # Calculate bandstop range
            low_freq = max(0.1, notch_freq - bandwidth / 2)
            high_freq = min(sampling_rate / 2 - 1, notch_freq + bandwidth / 2)

            # Apply bandstop filter using BrainFlow
            DataFilter.perform_bandstop(
                data=filtered_data,
                sampling_rate=int(sampling_rate),
                start_freq=low_freq,
                stop_freq=high_freq,
                order=order,
                filter_type=FilterTypes.BUTTERWORTH.value,
                ripple=0.0
            )

            logger.debug(f"Applied notch filter: {notch_freq} Hz (bandwidth: {bandwidth} Hz)")
            return filtered_data

        except InvalidFilterParametersError:
            raise
        except Exception as e:
            error_msg = f"Notch filtering failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def compute_psd(
        self,
        data: np.ndarray,
        sampling_rate: float,
        window: str = 'blackman_harris',
        nperseg: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Power Spectral Density using BrainFlow's Welch method.

        Args:
            data: Input signal data (1D array)
            sampling_rate: Sampling rate of the signal in Hz
            window: Window function to use (default: 'blackman_harris')
            nperseg: Length of each segment (default: nearest power of 2)

        Returns:
            Tuple of (frequencies, power_values)

        Raises:
            SignalProcessingException: If PSD computation fails
        """
        try:
            # Determine FFT size
            if nperseg is None:
                psd_size = DataFilter.get_nearest_power_of_two(int(sampling_rate))
            else:
                psd_size = nperseg

            # Ensure we have enough data
            if len(data) < psd_size:
                raise SignalProcessingException(
                    f"Insufficient data for PSD: need {psd_size}, got {len(data)}"
                )

            # Get window operation enum
            window_map = {
                'blackman_harris': WindowOperations.BLACKMAN_HARRIS.value,
                'hamming': WindowOperations.HAMMING.value,
                'hanning': WindowOperations.HANNING.value,
            }
            window_type = window_map.get(window, WindowOperations.BLACKMAN_HARRIS.value)

            # Compute PSD using BrainFlow
            psd_data = DataFilter.get_psd_welch(
                data=data,
                nfft=psd_size,
                overlap=psd_size // 2,
                sampling_rate=int(sampling_rate),
                window=window_type
            )

            # psd_data is a 2D array: [power_values, frequencies]
            power_values = psd_data[0]
            frequencies = psd_data[1]

            logger.debug(f"Computed PSD: {len(frequencies)} frequency bins")
            return frequencies, power_values

        except Exception as e:
            error_msg = f"PSD computation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def compute_band_power(
        self,
        psd_data: Tuple[np.ndarray, np.ndarray],
        band_range: Tuple[float, float]
    ) -> float:
        """
        Compute power in a specific frequency band using BrainFlow.

        Args:
            psd_data: Tuple of (frequencies, power_values) from compute_psd
            band_range: Tuple of (low_freq, high_freq) defining the band

        Returns:
            Power in the specified frequency band

        Raises:
            SignalProcessingException: If band power computation fails
        """
        try:
            frequencies, power_values = psd_data
            low_freq, high_freq = band_range

            # Validate band range
            if low_freq >= high_freq:
                raise InvalidFilterParametersError(
                    f"Low frequency ({low_freq}) must be less than high frequency ({high_freq})"
                )

            # Reconstruct PSD array for BrainFlow (2D array format)
            psd_array = np.array([power_values, frequencies])

            # Compute band power using BrainFlow
            band_power = DataFilter.get_band_power(psd_array, low_freq, high_freq)

            logger.debug(f"Computed band power for {low_freq}-{high_freq} Hz: {band_power:.4f}")
            return band_power

        except Exception as e:
            error_msg = f"Band power computation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def compute_eeg_bands(
        self,
        psd_data: Tuple[np.ndarray, np.ndarray]
    ) -> dict:
        """
        Compute power for all standard EEG bands.

        Args:
            psd_data: Tuple of (frequencies, power_values) from compute_psd

        Returns:
            Dictionary with band names as keys and power values as values
        """
        try:
            bands = {
                'delta': self.compute_band_power(psd_data, EEGBands.DELTA),
                'theta': self.compute_band_power(psd_data, EEGBands.THETA),
                'alpha': self.compute_band_power(psd_data, EEGBands.ALPHA),
                'beta': self.compute_band_power(psd_data, EEGBands.BETA),
                'gamma': self.compute_band_power(psd_data, EEGBands.GAMMA),
            }

            logger.debug(f"Computed EEG bands: {bands}")
            return bands

        except Exception as e:
            error_msg = f"EEG band computation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def detrend(self, data: np.ndarray, method: str = 'constant') -> np.ndarray:
        """
        Remove linear trend from the signal using BrainFlow.

        Args:
            data: Input signal data (1D array)
            method: Detrending method ('constant' or 'linear')

        Returns:
            Detrended signal data

        Raises:
            SignalProcessingException: If detrending fails
        """
        try:
            # Make a copy to avoid modifying original data
            detrended_data = data.copy()

            # Get detrend operation
            if method == 'constant':
                operation = DetrendOperations.CONSTANT.value
            elif method == 'linear':
                operation = DetrendOperations.LINEAR.value
            else:
                raise InvalidFilterParametersError(f"Unknown detrend method: {method}")

            # Apply detrending using BrainFlow
            DataFilter.detrend(detrended_data, operation)

            logger.debug(f"Applied {method} detrending")
            return detrended_data

        except InvalidFilterParametersError:
            raise
        except Exception as e:
            error_msg = f"Detrending failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)

    def apply_eeg_preprocessing(
        self,
        data: np.ndarray,
        sampling_rate: float,
        apply_detrend: bool = True,
        apply_bandpass: bool = True,
        apply_notch: bool = True,
        notch_freq: float = 50.0
    ) -> np.ndarray:
        """
        Apply standard EEG preprocessing pipeline.

        Args:
            data: Input signal data (1D array)
            sampling_rate: Sampling rate of the signal in Hz
            apply_detrend: Whether to apply detrending
            apply_bandpass: Whether to apply bandpass filter (1-59 Hz)
            apply_notch: Whether to apply notch filter
            notch_freq: Notch frequency (50 or 60 Hz)

        Returns:
            Preprocessed signal data
        """
        try:
            processed_data = data.copy()

            # 1. Detrend
            if apply_detrend:
                processed_data = self.detrend(processed_data, method='constant')

            # 2. Bandpass filter (1-59 Hz for EEG)
            if apply_bandpass:
                processed_data = self.apply_bandpass_filter(
                    processed_data,
                    sampling_rate,
                    low_freq=SignalProcessing.BANDPASS_LOW,
                    high_freq=SignalProcessing.BANDPASS_HIGH
                )

            # 3. Notch filter (remove line noise)
            if apply_notch:
                processed_data = self.apply_notch_filter(
                    processed_data,
                    sampling_rate,
                    notch_freq=notch_freq,
                    bandwidth=4.0
                )

            logger.debug("Applied EEG preprocessing pipeline")
            return processed_data

        except Exception as e:
            error_msg = f"EEG preprocessing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise SignalProcessingException(error_msg)
