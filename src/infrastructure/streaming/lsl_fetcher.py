"""
LSL Fetcher - Infrastructure component for LSL stream discovery.

This module provides optimized LSL stream discovery with async capabilities
and caching to prevent UI freezing.
"""

from pylsl import resolve_streams, StreamInfo
from PyQt5.QtCore import QThread, pyqtSignal
import time

from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class LSLDiscoveryThread(QThread):
    """
    Background thread for non-blocking LSL stream discovery.
    Prevents UI freezing during stream resolution.
    """
    streams_found = pyqtSignal(list)  # Emits list of StreamInfo objects

    def __init__(self, wait_time=1.0):
        super().__init__()
        self.wait_time = wait_time
        self.is_running = True

    def run(self):
        """Run stream discovery in background."""
        try:
            logger.debug(f"LSL Discovery Thread starting (wait_time={self.wait_time}s)...")
            streams = resolve_streams(wait_time=self.wait_time)
            logger.info(f"LSL Discovery Thread found {len(streams)} stream(s)")

            if self.is_running:  # Only emit if not cancelled
                self.streams_found.emit(streams)
        except Exception as e:
            logger.error(f"LSL Discovery Thread error: {e}")
            self.streams_found.emit([])

    def stop(self):
        """Stop the discovery thread."""
        self.is_running = False


class LSLFetcher:
    """
    OPTIMIZED LSL fetcher with async stream discovery and caching.

    This class provides methods to discover LSL streams either synchronously
    or asynchronously, with built-in caching to improve performance.
    """
    def __init__(self):
        self.cached_streams = []
        self.cache_timestamp = 0
        self.cache_ttl = 2.0  # Cache valid for 2 seconds
        self.discovery_thread = None
        logger.debug("LSLFetcher initialized")

    def get_available_streams(self, use_cache=True):
        """
        Get available streams (OPTIMIZED with caching).

        Args:
            use_cache: If True, return cached results if still valid

        Returns:
            List of StreamInfo objects
        """
        logger.debug("get_available_streams called")

        # Check cache first (optimization)
        if use_cache:
            cache_age = time.time() - self.cache_timestamp
            if cache_age < self.cache_ttl and self.cached_streams:
                logger.debug(f"Using cached streams ({len(self.cached_streams)} streams, age: {cache_age:.1f}s)")
                return self.cached_streams

        # Cache miss or expired - do discovery
        streams = resolve_streams(wait_time=0.1)  # OPTIMIZED: Minimal wait for instant discovery
        logger.info(f"Found {len(streams)} LSL stream(s)")
        for s in streams:
            logger.debug(f"  - {s.name()} ({s.type()}) - {s.channel_count()} channels")

        # Update cache
        self.cached_streams = streams
        self.cache_timestamp = time.time()

        return streams

    def get_available_streams_async(self, callback, wait_time=0.1):
        """
        Get available streams asynchronously (non-blocking).

        Args:
            callback: Function to call with list of StreamInfo objects
            wait_time: How long to wait for streams (default: 0.1s for instant discovery)
        """
        logger.debug("Starting async stream discovery...")

        # Stop any existing discovery
        if self.discovery_thread is not None and self.discovery_thread.isRunning():
            self.discovery_thread.stop()
            self.discovery_thread.wait()

        # Create and start new discovery thread
        self.discovery_thread = LSLDiscoveryThread(wait_time=wait_time)
        self.discovery_thread.streams_found.connect(callback)
        self.discovery_thread.start()

    def clear_cache(self):
        """Clear the stream cache."""
        self.cached_streams = []
        self.cache_timestamp = 0
        logger.debug("Stream cache cleared")
