import logging
from threading import Event, Thread
from time import sleep, time

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError, BrainFlowExitCodes, BrainFlowPresets

class SensorInterface:
    def connect(self):
        raise NotImplementedError("connect method must be implemented")
        
    def disconnect(self):
        raise NotImplementedError("disconnect method must be implemented")
        
    def get_status(self):
        raise NotImplementedError("get_status method must be implemented")

class MuseBrainFlowSensor(SensorInterface):
    """
    A sensor class that, once connected, runs a background thread to
    maintain a continuous BrainFlow session. If data are not received
    for `timeout` seconds, the background thread attempts to release
    and then re-prepare the board.
    """

    def __init__(self, candidate_board_ids=None, streamer_params=None, timeout=30):
        """
        :param candidate_board_ids: List of BrainFlow board IDs to try
        :param streamer_params:     BrainFlow streamer params, e.g. 'file://data.csv:w'
        :param timeout:            No new data after `timeout` seconds => attempt to reconnect
        """
        self.streamer_params = streamer_params
        self.timeout = timeout

        # BoardShim will be created by the handler thread once it picks a working board ID
        self.board_shim = None
        self.brainflow_thread = None

        # Use an Event to keep the background thread alive
        self.stay_alive = Event()
        self.stay_alive.clear()

        if candidate_board_ids is None:
            candidate_board_ids = [
                BoardIds.MUSE_2016_BOARD,
                BoardIds.MUSE_2_BOARD,
                BoardIds.MUSE_S_BOARD
            ]
        self.candidate_board_ids = candidate_board_ids

        # Store BrainFlow input params; some boards need e.g. serial_port, mac_address, etc.
        self.params = BrainFlowInputParams()
        self.params.timeout = timeout

        # For status checks
        self.connected = False

    def connect(self):
        """
        Launches a background thread that tries each candidate board ID in a loop.
        Once it finds a board that can be prepared, it will start streaming data.
        If data go stale (no new samples for `timeout` seconds), it will release
        the session and attempt to prepare it again (still in the background).
        """
        if self.connected:
            logging.info("Already connected, ignoring.")
            return True

        # Start the background thread that handles board creation, session prep, timeouts, etc.
        self.stay_alive.set()
        self.brainflow_thread = BrainFlowHandler(
            sensor=self,
            stay_alive=self.stay_alive,
            streamer_params=self.streamer_params,
            timeout=self.timeout
        )
        self.brainflow_thread.start()
        sleep(1.0)

        # Mark ourselves "connected" in the sense of "we're trying to connect + keep alive"
        self.connected = True
        
        return True

    def disconnect(self):
        """
        Signal the background thread to stop, wait for it to join,
        and mark ourselves disconnected.
        """
        if not self.connected:
            logging.info("Already disconnected, ignoring.")
            return
        self.stay_alive.clear()
        if self.brainflow_thread is not None:
            self.brainflow_thread.join(timeout=5)
        # Release any leftover board sessions
        self.release_brainflow()
        self.connected = False

    def is_alive(self):
        """
        Simple check to see if the board_shim is prepared (i.e., streaming).
        Returns False if we aren't actively trying to connect or if there's no board_shim.
        """
        if not self.connected:
            return False
        if not self.board_shim:
            return False
        return self.board_shim.is_prepared()

    def release_brainflow(self):
        logging.info("Releasing all brainflow sessions from sensor.")
        try:
            # If a board_shim is active, release all sessions
            BoardShim.release_all_sessions()
        except BrainFlowError as e:
            logging.exception(e)

    # Optional: Let other parts of the code ask for the underlying BoardShim
    def get_board(self):
        return self.board_shim


class BrainFlowHandler(Thread):
    """
    Thread that tries to keep a BrainFlow session alive for the MuseBrainFlowSensor.
    - Loops while 'stay_alive' is set.
    - If board is not prepared, tries candidate board IDs to prepare + start streaming.
    - Once streaming, it checks timestamps to see if data is still flowing.
      If no data for 'timeout' seconds, we release the session and attempt to re-prepare.
    """

    def __init__(self, sensor: MuseBrainFlowSensor,
                 stay_alive: Event,
                 streamer_params: str = None,
                 timeout: int = 30,
                 thread_name: str = "thread_brainflow",
                 thread_daemon: bool = False):
        """
        :param sensor:         The MuseBrainFlowSensor instance
        :param stay_alive:     Thread runs while this event is True.
        :param streamer_params: BrainFlow streaming param (e.g. file://filename:mode).
        :param timeout:        If we see no new data for 'timeout' seconds, attempt reconnect.
        """
        super().__init__(name=thread_name, daemon=thread_daemon)
        self.sensor = sensor
        self.stay_alive = stay_alive
        self.streamer_params = streamer_params
        self.timeout = timeout

        # last data timestamp to detect timeouts
        self.last_timestamp = time()

    def run(self):
        while self.stay_alive.is_set():
            board_shim = self.sensor.board_shim

            if not board_shim or (board_shim and not board_shim.is_prepared()):
                # We have no valid prepared session => try to connect
                self._prepare_board_shim()
                # short sleep so we don't spam prepare calls in a tight loop
                sleep(2.0)
            else:
                # Board is prepared. Check for data
                newest_ts = self._get_newest_timestamp(board_shim)
                current_time = time()

                if newest_ts is not None:
                    self.last_timestamp = newest_ts

                if (current_time - self.last_timestamp) > self.timeout:
                    logging.warning("No new data within timeout, releasing session to attempt reconnect.")
                    try:
                        board_shim.release_session()
                    except Exception as e:
                        logging.error(f"Exception while releasing board: {e}")
                    self.connected = False
                    # short pause, then loop tries to re-prepare in next iteration
                    sleep(2.0)
                else:
                    # Otherwise, data is flowing; we wait a bit and re-check
                    sleep(2.0)

    def _prepare_board_shim(self):
        """
        Attempt to create/prepare a BoardShim for each candidate board ID
        until successful or we exhaust them. On success, store the BoardShim
        in self.sensor.board_shim and start streaming.
        """
        # If we already had a board_shim, release it first to avoid conflicts
        if self.sensor.board_shim:
            try:
                self.sensor.board_shim.release_session()
            except Exception:
                pass
            self.sensor.board_shim = None

        for bid in self.sensor.candidate_board_ids:
            if not self.stay_alive.is_set():
                return  # if user disconnected mid-loop
            try:
                logging.info(f"[BrainFlowHandler] Attempting board id {bid}...")
                board = BoardShim(bid, self.sensor.params)
                board.prepare_session()
                logging.info(f"[BrainFlowHandler] Board {bid} prepared. Starting stream.")
                board.start_stream(45000, self.streamer_params)
                self.sensor.board_shim = board
                logging.info(f"[BrainFlowHandler] Successfully started streaming on board id {bid}.")
                return  # success => break out
            except BrainFlowError as e:
                logging.warning(f"Failed to prepare board {bid}: {e}")
                try:
                    board.release_session()
                except Exception:
                    pass
            except Exception as e:
                logging.warning(f"Generic exception in preparing board {bid}: {e}")

        logging.error("[BrainFlowHandler] All candidate board IDs failed. Will keep retrying...")

    def _get_newest_timestamp(self, board_shim: BoardShim):
        """
        Return the newest timestamp from the ring buffer, or None if no data is available.
        """
        try:
            count = board_shim.get_board_data_count(BrainFlowPresets.DEFAULT_PRESET)
            if count == 0:
                return None  # no data => None
            # retrieve the last piece of data
            data = board_shim.get_current_board_data(count, BrainFlowPresets.DEFAULT_PRESET)
            time_channel = board_shim.get_timestamp_channel(board_shim.get_board_id(), BrainFlowPresets.DEFAULT_PRESET)
            newest_ts = data[time_channel, -1]
            return newest_ts
        except BrainFlowError as e:
            logging.error(f"BrainFlow error in _get_newest_timestamp: {e}")
        except Exception as ex:
            logging.error(f"Exception in _get_newest_timestamp: {ex}")
        return None

    def __del__(self):
        # A fallback in case thread is garbage‐collected before .disconnect is called
        self.sensor.release_brainflow()
