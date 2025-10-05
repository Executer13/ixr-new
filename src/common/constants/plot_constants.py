"""
Plot Constants - Centralized constants for plotting and visualization.

This module contains all hardcoded values related to plot configuration,
signal processing, and visualization settings.
"""

from enum import Enum


class PlotDefaults:
    """Default settings for plotting."""

    # Time window settings
    DEFAULT_TIME_WINDOW = 10.0  # seconds
    MIN_TIME_WINDOW = 0.1       # seconds
    MAX_TIME_WINDOW = 60.0      # seconds
    TIME_WINDOW_STEP = 0.5      # seconds

    # Refresh and performance settings
    REFRESH_RATE = 20.0         # fps
    MAX_PLOT_POINTS = 2000      # maximum points to plot (for decimation)

    # PSD settings
    PSD_WINDOW_SECONDS = 2.0    # seconds of data for PSD calculation
    PSD_FREQUENCY_LIMIT = 60    # Hz

    # Plot dimensions
    MIN_PLOT_HEIGHT = 150       # pixels
    MIN_PSD_HEIGHT = 250        # pixels
    MIN_BAND_HEIGHT = 250       # pixels


class SignalProcessing:
    """Constants for signal processing."""

    # Filter settings
    DEFAULT_CUTOFF_FREQ = 40.0  # Hz
    FILTER_ORDER = 4            # IIR filter order

    # Bandpass filter (for EEG)
    BANDPASS_LOW = 1.0          # Hz
    BANDPASS_HIGH = 59.0        # Hz
    BANDPASS_ORDER = 2

    # Notch filter (line noise removal)
    NOTCH_FREQ_50HZ = 50.0      # Hz (Europe, most of world)
    NOTCH_FREQ_60HZ = 60.0      # Hz (US, Americas)
    NOTCH_LOW = 48.0            # Hz
    NOTCH_HIGH = 52.0           # Hz
    NOTCH_ORDER = 2

    # PSD settings
    PSD_OVERLAP_RATIO = 0.5     # 50% overlap for Welch's method

    # Normalization
    NORMALIZATION_EPSILON = 1e-12  # Small value to prevent division by zero


class EEGBands:
    """EEG frequency band definitions."""

    DELTA = (1.0, 4.0)      # Hz
    THETA = (4.0, 8.0)      # Hz
    ALPHA = (8.0, 13.0)     # Hz
    BETA = (13.0, 30.0)     # Hz
    GAMMA = (30.0, 60.0)    # Hz

    BAND_NAMES = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]

    @classmethod
    def get_all_bands(cls):
        """Get all band definitions as a dictionary."""
        return {
            "Delta": cls.DELTA,
            "Theta": cls.THETA,
            "Alpha": cls.ALPHA,
            "Beta": cls.BETA,
            "Gamma": cls.GAMMA
        }


class PlotColors:
    """Color definitions for plots."""

    # Original color palette
    PALETTE = [
        '#e9c46a', '#f4a261', '#e76f51', '#d62828',
        '#2a9d8f', '#168aad', '#e9f5db', '#A57E2F', '#A53B2F'
    ]

    # EEG channel colors (vibrant palette)
    EEG_COLORS = [
        '#3b82f6',  # Blue
        '#8b5cf6',  # Purple
        "#032F76",  # Dark Blue
          "#4e3bf6",  # Blue
    ]


class StreamTypeRanges:
    """Y-axis ranges for different stream types."""

    EEG = (-150, 150)           # microvolts
    GYRO = (-200, 200)          # degrees/sec
    PPG = (-1500, 2000)         # arbitrary units
    ECG = (-1500, 2000)         # microvolts

    @classmethod
    def get_range(cls, stream_type: str):
        """
        Get the appropriate Y-axis range for a stream type.

        Args:
            stream_type: Type of stream (EEG, GYRO, PPG, ECG)

        Returns:
            Tuple of (min, max) for Y-axis range
        """
        stream_type = stream_type.upper()

        if "EEG" in stream_type:
            return cls.EEG
        elif "GYRO" in stream_type or "MOTION" in stream_type:
            return cls.GYRO
        elif "PPG" in stream_type or "HEART" in stream_type:
            return cls.PPG
        elif "ECG" in stream_type:
            return cls.ECG
        else:
            return cls.EEG  # Default to EEG range


class GridSettings:
    """Grid display settings."""

    SHOW_GRID = True
    GRID_ALPHA = 0.25           # transparency (0-1)
    GRID_ALPHA_WHITE_BG = 0.3   # transparency for white background
