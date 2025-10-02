# brainflow_LSL_publisher.py

import time
from threading import Event, Thread

from brainflow import (BoardShim, BrainFlowError, BrainFlowExitCodes, BrainFlowPresets)
from pylsl import StreamInfo, StreamOutlet, cf_double64, local_clock


class BrainFlowLSLPublisher(Thread):
    """
    Persistent LSL Publisher.
    
    This publisher creates its LSL outlets once (in __init__) and then continuously
    runs in its own thread. It checks a 'streaming_enabled' flag to decide whether to push data.
    
    To pause streaming, clear the streaming_enabled event.
    To resume streaming, set the streaming_enabled event.
    The do_stream event controls the lifetime of the thread.
    """

    def __init__(self, board_shim: BoardShim, stay_alive: Event, streaming_enabled: Event,
                 thread_name: str = "lsl_data_pusher", thread_daemon: bool = False) -> None:
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
            #logging.info(f"Creating persistent LSL outlet for {name}.")
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
            #logging.info(f"Persistent LSL outlet created for {data_type} (name: {info_data.name()}).")

        self.previous_timestamp = {'eeg': 0, 'gyro': 0, 'ppg': 0}
        self.local2lsl_time_diff = time.time() - local_clock()  # compute offset.

    def update_board(self, new_board_shim: BoardShim):
        """
        Update the board_shim for the publisher when reconnecting.
        """
        self.board_shim = new_board_shim
        self.board_id = new_board_shim.get_board_id()
        # Optionally reset timestamps.
        self.previous_timestamp = {k: 0 for k in self.previous_timestamp}
        #logging.info("LSL publisher: board updated.")

    def run(self) -> None:
        """Main loop: while do_stream is set, check if streaming is enabled and push data."""
        while self.stay_alive.is_set():
            if self.streaming_enabled.is_set():
                # print("brainflow lslpublisher")
                if not self.board_shim.is_prepared():
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

    def get_channels(self, preset: BrainFlowPresets) -> dict[int, str]:
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
