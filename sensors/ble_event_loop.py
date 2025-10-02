# ble_event_loop.py

import asyncio
import threading

class BleEventLoop:
    """
    A helper class to manage a single background event loop in a dedicated thread.
    We run all BLE coroutines on this loop to avoid 'Event loop is closed' issues.
    """

    _instance = None

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_loop_runner, daemon=True)
        self.thread.start()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = BleEventLoop()
        return cls._instance

    def _thread_loop_runner(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_in_loop(self, coro):
        """
        Schedule a coroutine on the event loop, returning a concurrent.futures.Future.
        """
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        """
        If you want to shut down the loop:
        """
        def stopper():
            self.loop.stop()
        self.loop.call_soon_threadsafe(stopper)
        self.thread.join()
