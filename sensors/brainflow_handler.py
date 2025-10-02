# brainflow_handler.py

import time
import threading
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BrainFlowPresets
from brainflow import BoardIds

class BrainFlowHandler:
    def __init__(self, board_id, input_params: BrainFlowInputParams, check_interval=1.0, timeout=5.0):
        """
        board_id: integer id for the board (e.g., from BrainFlow BoardIds)
        input_params: a BrainFlowInputParams instance with connection parameters
        check_interval: seconds between alive checks
        timeout: seconds after which board is considered unresponsive if no new data
        """
        self.board_id = board_id
        self.input_params = input_params
        self.check_interval = check_interval
        self.timeout = timeout
        self.board = None
        self.alive = False
        # Replace boolean flag with a threading.Event for stopping the thread.
        self._stop_event = threading.Event()
        self._check_thread = None

    def prepare_and_connect_board(self):
        """
        Prepare the BrainFlow session and start the data stream.
        Also starts a background thread to monitor board health.
        """
        try:
            
            self.board = BoardShim(self.board_id, self.input_params)
            self.board.prepare_session()
            if self.board_id in [BoardIds.MUSE_2_BOARD, BoardIds.MUSE_S_BOARD]:
                self.board.config_board("p50")  # Sets 5th EEG and PPG for Muse 2. Sets 5th EEG for Muse S.
                self.board.config_board("p61")  # Sets PPG for Muse S, only works if p50 is set.
        
            # Start streaming; adjust buffer size or other parameters as needed.
            self.board.start_stream(45000)
            self.alive = True
            # Clear the stop event and start the background thread
            self._stop_event.clear()
            self._check_thread = threading.Thread(target=self._check_alive_loop, daemon=True)
            self._check_thread.start()
            print("Board connected and stream started.")
        except Exception as e:
            print("Error during board connection:", e)
            self.alive = False

    def _check_alive_loop(self):
        print("_check_alive_loop")
        """
        Continuously check if new data is arriving by comparing the latest timestamp
        from the board data with the current time.
        """
        last_timestamp = time.time()
        while not self._stop_event.is_set():
            try:
                data_count = self.board.get_board_data_count()
                if data_count > 0:
                    data_timestamp = self.board.get_current_board_data(1, BrainFlowPresets.DEFAULT_PRESET)[
                        self.board.get_timestamp_channel(self.board_id, BrainFlowPresets.DEFAULT_PRESET)]
                    if len(data_timestamp) > 0:
                        last_timestamp = float(data_timestamp)
                # If no new data is received for longer than timeout, consider connection dead.
                current_time = time.time()
                if current_time - last_timestamp > self.timeout:
                    self.alive = False
                else:
                    self.alive = True
            except Exception as e:
                print("Error checking board alive status:", e)
                self.alive = False
            time.sleep(self.check_interval)

    def is_alive(self):
        """Return True if the board appears to be streaming data; otherwise False."""
        return self.alive

    def delete_board(self):
        """
        Stop the data stream and release the BrainFlow session.
        Also stops the background thread.
        """
        # Signal the thread to stop
        self._stop_event.set()
        # Wait for the thread to finish
        if self._check_thread is not None:
            self._check_thread.join()
        if self.board is not None:
            try:
                self.board.stop_stream()
                self.board.release_session()
                print("Board stream stopped and session released.")
            except Exception as e:
                print("Error during board deletion:", e)
            finally:
                self.board = None
