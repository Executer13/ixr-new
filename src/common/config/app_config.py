"""
Application Configuration - Centralized configuration management.

This module provides a centralized way to manage application configuration,
supporting environment-specific settings and runtime updates.
"""

import json
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SensorConfig:
    """Configuration for sensor operations."""
    auto_reconnect: bool = True
    reconnect_interval: float = 2.0
    connection_timeout: float = 5.0
    status_check_interval: float = 1.0


@dataclass
class PlotConfig:
    """Configuration for plotting operations."""
    default_time_window: float = 10.0
    refresh_rate: float = 20.0
    max_plot_points: int = 2000
    enable_opengl: bool = True
    show_grid: bool = True


@dataclass
class AnalysisConfig:
    """Configuration for analysis operations."""
    calibration_length: int = 600
    power_length: int = 10
    scale: float = 1.5
    offset: float = 0.5
    head_impact: float = 0.2
    longerterm_length: int = 30
    reference: str = "mean"


@dataclass
class AppConfig:
    """Main application configuration."""
    # Window settings
    window_width: int = 1400
    window_height: int = 1200
    window_x: int = 100
    window_y: int = 100

    # Component configs
    sensor: SensorConfig = None
    plot: PlotConfig = None
    analysis: AnalysisConfig = None

    # Logging
    log_level: str = "INFO"
    log_file: str = "ixr_suite.log"

    # Development
    debug_mode: bool = False

    def __post_init__(self):
        """Initialize sub-configurations if not provided."""
        if self.sensor is None:
            self.sensor = SensorConfig()
        if self.plot is None:
            self.plot = PlotConfig()
        if self.analysis is None:
            self.analysis = AnalysisConfig()


class ConfigManager:
    """
    Manages application configuration with support for:
    - Loading from JSON files
    - Environment-specific configurations
    - Runtime updates
    - Saving configurations
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        self._config = AppConfig()
        self._config_path = config_path or self._get_default_config_path()

        # Load configuration if file exists
        if os.path.exists(self._config_path):
            self.load()

    @staticmethod
    def _get_default_config_path() -> str:
        """Get the default configuration file path."""
        # Store config in user's home directory
        home = Path.home()
        config_dir = home / ".ixr_suite"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "config.json")

    def load(self) -> None:
        """Load configuration from file."""
        try:
            with open(self._config_path, 'r') as f:
                data = json.load(f)

            # Update sensor config
            if 'sensor' in data:
                self._config.sensor = SensorConfig(**data['sensor'])

            # Update plot config
            if 'plot' in data:
                self._config.plot = PlotConfig(**data['plot'])

            # Update analysis config
            if 'analysis' in data:
                self._config.analysis = AnalysisConfig(**data['analysis'])

            # Update main config
            for key in ['window_width', 'window_height', 'window_x', 'window_y',
                       'log_level', 'log_file', 'debug_mode']:
                if key in data:
                    setattr(self._config, key, data[key])

        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Continue with default configuration

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            config_dict = {
                'window_width': self._config.window_width,
                'window_height': self._config.window_height,
                'window_x': self._config.window_x,
                'window_y': self._config.window_y,
                'log_level': self._config.log_level,
                'log_file': self._config.log_file,
                'debug_mode': self._config.debug_mode,
                'sensor': asdict(self._config.sensor),
                'plot': asdict(self._config.plot),
                'analysis': asdict(self._config.analysis)
            }

            with open(self._config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)

        except Exception as e:
            print(f"Error saving configuration: {e}")

    def get(self) -> AppConfig:
        """Get the current configuration."""
        return self._config

    def update(self, **kwargs) -> None:
        """
        Update configuration values.

        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = AppConfig()


# Global configuration instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        ConfigManager: The global configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """
    Get the current application configuration.

    Returns:
        AppConfig: Current configuration
    """
    return get_config_manager().get()
