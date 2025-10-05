"""
BLE Event Loop - Infrastructure component for managing BLE event loops.

This module provides a singleton event loop for managing Bluetooth Low Energy
operations in a dedicated thread, avoiding 'Event loop is closed' issues.
Cross-platform compatible (Windows, macOS, Linux).
"""

import asyncio
import threading
import sys

from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class BleEventLoop:
    """
    A helper class to manage a single background event loop in a dedicated thread.
    We run all BLE coroutines on this loop to avoid 'Event loop is closed' issues.

    This is implemented as a singleton to ensure only one event loop exists.

    Platform Support:
    - Windows: Uses ProactorEventLoop (required for BLE on Windows)
    - macOS/Linux: Uses default SelectorEventLoop
    """

    _instance = None

    def __init__(self):
        # Platform-specific event loop creation
        if sys.platform == 'win32':
            # Windows requires ProactorEventLoop for proper BLE/subprocess support
            logger.debug("Creating ProactorEventLoop for Windows")
            self.loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
        else:
            # macOS and Linux use the default event loop
            logger.debug(f"Creating default event loop for {sys.platform}")
            self.loop = asyncio.new_event_loop()

        self.thread = threading.Thread(target=self._thread_loop_runner, daemon=True)
        self.thread.start()
        logger.info(f"BLE event loop initialized for {sys.platform}")

    @classmethod
    def instance(cls):
        """Get the singleton instance of the BLE event loop."""
        if cls._instance is None:
            cls._instance = BleEventLoop()
        return cls._instance

    def _thread_loop_runner(self):
        """Thread runner that sets and runs the event loop forever."""
        asyncio.set_event_loop(self.loop)
        logger.debug("BLE event loop thread started")
        self.loop.run_forever()

    def run_in_loop(self, coro):
        """
        Schedule a coroutine on the event loop, returning a concurrent.futures.Future.

        Args:
            coro: The coroutine to run in the event loop

        Returns:
            concurrent.futures.Future representing the scheduled coroutine
        """
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        """
        Stop the event loop and join the thread.
        Use this for graceful shutdown.
        """
        def stopper():
            self.loop.stop()
        self.loop.call_soon_threadsafe(stopper)
        self.thread.join()
        logger.info("BLE event loop stopped")
