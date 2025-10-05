"""
BrainFlow LSL Publisher - Infrastructure component for publishing BrainFlow data to LSL.

This module provides a persistent LSL publisher that continuously streams
BrainFlow data to Lab Streaming Layer outlets.
"""

import time
from threading import Event, Thread

from brainflow import BoardShim, BrainFlowError, BrainFlowExitCodes, BrainFlowPresets
from pylsl import StreamInfo, StreamOutlet, cf_double64, local_clock

from src.common.utils.logger import get_logger

logger = get_logger(__name__)


class BrainFlowLSLPublisher(Thread):
    """
    Persistent LSL Publisher for BrainFlow data.

    This publisher creates its LSL outlets once (in __init__) and then continuously
    runs in its own thread. It checks a 'streaming_enabled' flag to decide whether to push data.

    To pause streaming, clear the streaming_enabled event.
    To resume streaming, set the streaming_enabled event.
    The stay_alive event controls the lifetime of the thread.
    """

    def __init__(self, board_shim: BoardShim, stay_alive: Event, streaming_enabled: Event,
                 thread_name: str = "lsl_data_pusher", thread_daemon: bool = False) -> None:
        """
        Initialize the LSL publisher.

        Args:
            board_shim: BrainFlow BoardShim instance
            stay_alive: Event controlling overall thread lifetime
            streaming_enabled: Event controlling data pushing
            thread_name: Name for the thread
            thread_daemon: Whether thread should be daemon
        """
        Thread.__init__(self, name=thread_name, daemon=thread_daemon)
        self.stay_alive = stay_alive  # Controls overall thread lifetime.
        self.streaming_enabled = streaming_enabled  # Controls data pushing.
        self.board_shim = board_shim
        self.board_id = board_shim.get_board_id()

        # Determine available presets.
        all_presets = BoardShim.get_board_presets(self.board_id)
        presets = {
            'eeg': BrainFlowPresets.DEFAULT_PRESET,
            'gyro': BrainFlowPresets.AUXILIARY_PRESET,
            'ppg': BrainFlowPresets.ANCILLARY_PRESET,
        }
        self.data_types = {}  # e.g. {'eeg': preset, ...}
        for data_type, preset in presets.items():
            if preset in all_presets:
                description = BoardShim.get_board_descr(self.board_id, preset)
                if (data_type + "_channels") in description:
                    self.data_types[data_type] = preset

        self.channels = {k: self.get_channels(v) for k, v in self.data_types.items()}

        # Create persistent LSL outlets.
        self.outlets = {}
        for data_type, preset in self.data_types.items():
            rate = self.board_shim.get_sampling_rate(self.board_id, preset)
            name = f'ixr-suite-{data_type}-data'
            channel_count = len(self.channels[data_type])
            logger.info(f"Creating persistent LSL outlet for {name} with {channel_count} channels at {rate} Hz")
            info_data = StreamInfo(name=name, type=data_type.upper(), channel_count=channel_count,
                                   nominal_srate=rate, channel_format=cf_double64,
                                   source_id='ixr-suite-lsl-data-publisher')
            stream_channels = info_data.desc().append_child("channels")
            for _, label in self.channels[data_type].items():
                ch = stream_channels.append_child("channel")
                ch.append_child_value("label", label)
                if data_type == 'eeg':
                    ch.append_child_value("unit", 'microvolts')
                ch.append_child_value("type", data_type)
            self.outlets[data_type] = StreamOutlet(info_data)
            logger.info(f"Persistent LSL outlet created for {data_type} (name: {info_data.name()})")

        self.previous_timestamp = {'eeg': 0, 'gyro': 0, 'ppg': 0}
        self.local2lsl_time_diff = time.time() - local_clock()  # compute offset.

    def update_board(self, new_board_shim: BoardShim):
        """
        Update the board_shim for the publisher when reconnecting.

        Args:
            new_board_shim: New BoardShim instance
        """
        self.board_shim = new_board_shim
        self.board_id = new_board_shim.get_board_id()
        # Optionally reset timestamps.
        self.previous_timestamp = {k: 0 for k in self.previous_timestamp}
        logger.info("LSL publisher: board updated")

    def run(self) -> None:
        """Main loop: while stay_alive is set, check if streaming is enabled and push data."""
        logger.info("LSL Publisher thread started, entering main loop")
        iteration_count = 0
        while self.stay_alive.is_set():
            if iteration_count == 0 or iteration_count % 100 == 0:
                logger.debug(f"Loop iteration {iteration_count}, streaming_enabled={self.streaming_enabled.is_set()}")
            iteration_count += 1

            if self.streaming_enabled.is_set():
                if not self.board_shim.is_prepared():
                    if iteration_count % 100 == 0:
                        logger.debug("Board not prepared yet...")
                    time.sleep(0.1)
                    continue

                for data_type, preset in self.data_types.items():
                    timestamp_column = self.board_shim.get_timestamp_channel(self.board_id, preset)
                    try:
                        data = self.board_shim.get_current_board_data(1024, preset)
                    except BrainFlowError as e:
                        if e.exit_code == BrainFlowExitCodes.INVALID_ARGUMENTS_ERROR:
                            continue
                        else:
                            raise e

                    data = data[:, data[timestamp_column] > self.previous_timestamp[data_type]]
                    if data.shape[1] > 0:
                        self.previous_timestamp[data_type] = data[timestamp_column, -1]
                        data = data[list(self.channels[data_type].keys()), :]
                        self.outlets[data_type].push_chunk(
                            data.T.tolist(),
                            self.previous_timestamp[data_type] - self.local2lsl_time_diff
                        )
                # Sleep according to sampling rate.
                srate = self.board_shim.get_sampling_rate(self.board_id,
                           self.data_types[list(self.data_types.keys())[0]])
                time.sleep(1.0 / srate)
            else:
                # If streaming is paused, sleep briefly.
                time.sleep(0.1)

        logger.info("LSL Publisher thread exiting")

    def get_channels(self, preset: BrainFlowPresets) -> dict[int, str]:
        """
        Get channel mapping for a given preset.

        Args:
            preset: BrainFlow preset to get channels for

        Returns:
            Dictionary mapping channel indices to channel names

        Raises:
            ValueError: If preset is unrecognized
        """
        channels = {}
        description = BoardShim.get_board_descr(self.board_id, preset)
        if preset == BrainFlowPresets.DEFAULT_PRESET:
            channels.update(dict(zip(description['eeg_channels'], description['eeg_names'].split(","))))
        elif preset == BrainFlowPresets.AUXILIARY_PRESET:
            channels.update({channel: f"accel_{i}" for i, channel in enumerate(description['accel_channels'])})
            channels.update({channel: f"gyro_{i}" for i, channel in enumerate(description['gyro_channels'])})
        elif preset == BrainFlowPresets.ANCILLARY_PRESET:
            channels.update({channel: f"ppg_{i}" for i, channel in enumerate(description['ppg_channels'])})
        else:
            raise ValueError("Unrecognized BrainFlowPresets")
        return channels
