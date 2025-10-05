"""
Brain Power Worker - Application service for brain power analysis.

This worker thread performs brain power analysis based on the original IXR Suite logic.
Uses BrainFlow directly (not LSL) to match original implementation.
"""

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from scipy.signal import butter, filtfilt, welch
from dataclasses import dataclass
from brainflow import BoardShim, BrainFlowPresets, BrainFlowError, BrainFlowExitCodes

from src.common.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Channel:
    """Represents an EEG or sensor channel."""
    ch_number: int
    name: str
    reference: bool
    display: bool


class BrainPowerWorker(QThread):
    """
    Worker thread that performs brain power analysis based on the original IXR Suite logic.
    Uses BrainFlow directly (not LSL) to match original implementation.

    Signals:
        analysisUpdated: Emitted with (final_power, short_term_power, long_term_power, band_powers_list)
        statusUpdated: Emitted with status messages
    """

    analysisUpdated = pyqtSignal(float, float, float, list)
    statusUpdated = pyqtSignal(str)

    def __init__(self, settings, board_shim):
        super().__init__()
        self.settings = settings
        self.board_shim = board_shim
        self.board_id = board_shim.get_board_id()
        self._running = True

        # Get available presets for the specific board
        self.available_presets = BoardShim.get_board_presets(self.board_id)

        # Setup EEG preset
        if BrainFlowPresets.DEFAULT_PRESET in self.available_presets:
            self.eeg_preset = BrainFlowPresets.DEFAULT_PRESET
            eeg_description = BoardShim.get_board_descr(self.board_id, self.eeg_preset)
            logger.info(f"EEG description: {eeg_description}")

            # Create EEG channel objects
            self.eeg_channels = [
                Channel(ch_number, eeg_description['eeg_names'].split(',')[i], False, True)
                for i, ch_number in enumerate(eeg_description['eeg_channels'])
            ]

            # Add reference channels
            if 'other_channels' in eeg_description:
                self.eeg_channels += [
                    Channel(ch_number, 'Fpz', True, False)
                    for ch_number in eeg_description['other_channels']
                ]

            self.eeg_sr = BoardShim.get_sampling_rate(self.board_id, self.eeg_preset)
            logger.info(f"EEG sample rate: {self.eeg_sr} Hz")
        else:
            raise RuntimeError("DEFAULT_PRESET not available for this board")

        # Setup GYRO preset
        if BrainFlowPresets.AUXILIARY_PRESET in self.available_presets:
            self.gyro_preset = BrainFlowPresets.AUXILIARY_PRESET
            gyro_description = BoardShim.get_board_descr(self.board_id, self.gyro_preset)
            logger.info(f"GYRO description: {gyro_description}")

            if 'gyro_channels' in gyro_description:
                self.gyro_channels = [
                    Channel(ch_number, f"gyro {i+1}", False, True)
                    for i, ch_number in enumerate(gyro_description['gyro_channels'])
                ]
            else:
                self.gyro_channels = []

            self.gyro_sr = BoardShim.get_sampling_rate(self.board_id, self.gyro_preset)
            logger.info(f"GYRO sample rate: {self.gyro_sr} Hz")
        else:
            self.gyro_channels = []
            self.gyro_sr = 52.0  # Default for Muse
            logger.warning("AUXILIARY_PRESET not available, GYRO disabled")

        # Brain power metrics
        self.update_speed_ms = 40  # Update every 40ms for real-time (match original IXR-Suite)
        self.power_metric_window_s = 1.5
        self.psd_size = 2**int(np.floor(np.log2(self.eeg_sr)))

        # Calibration and history
        self.inverse_workload_calib = [0, 1]
        self.inverse_workload_hist = [0, 1]
        self.inverse_workload = 0
        self.engagement_calib = [0, 1]
        self.engagement_hist = [0, 1]
        self.engagement = 0
        self.power_metrics = 0
        self.longerterm_hist = [0]

        # Parameters (will be set from settings)
        self.calib_length = 0
        self.hist_length = 0
        self.longerterm_length = 0
        self.brain_scale = 1.0
        self.brain_center = 0.4
        self.head_impact = 0.2

    def set_parameters(self):
        """Convert settings to internal parameters."""
        self.calib_length = int(self.settings["calib_length"] * 1000 / self.update_speed_ms)
        self.hist_length = int(self.settings["power_length"] * 1000 / self.update_speed_ms)
        self.longerterm_length = int(self.settings["longerterm_length"] * 1000 / self.update_speed_ms)
        self.brain_scale = self.settings["scale"]
        self.brain_center = self.settings["offset"]
        self.head_impact = self.settings["head_impact"]

    def run(self):
        """Main processing loop - uses BrainFlow directly."""
        logger.info("=" * 60)
        logger.info("Brain Power Worker: Starting analysis (BrainFlow mode)...")
        logger.info("=" * 60)

        self.set_parameters()
        logger.info(f"Parameters set - calib={self.calib_length}, hist={self.hist_length}, scale={self.brain_scale}")

        self.statusUpdated.emit("Waiting for board to be ready...")

        # Wait for board to be prepared
        while self._running and not self.board_shim.is_prepared():
            logger.debug("Waiting for board to be prepared...")
            self.msleep(500)

        if not self._running:
            logger.info("Stopped before board was ready")
            return

        logger.info("Board is ready! Entering main processing loop...")
        self.statusUpdated.emit("Running...")

        while self._running:
            try:
                # Check if board is still prepared
                if not self.board_shim.is_prepared():
                    logger.warning("Board no longer prepared, stopping...")
                    self.statusUpdated.emit("Board disconnected")
                    break

                # Pull EEG data directly from BrainFlow (like original implementation)
                try:
                    eeg_data = self.board_shim.get_current_board_data(
                        int(self.power_metric_window_s * self.eeg_sr),
                        self.eeg_preset
                    )
                except BrainFlowError as e:
                    # Right after board preparation, connection might be unstable
                    if e.exit_code == BrainFlowExitCodes.INVALID_ARGUMENTS_ERROR:
                        self.msleep(self.update_speed_ms)
                        continue
                    else:
                        raise e

                # Check if we got enough data
                if len(eeg_data) < 1 or eeg_data.shape[1] < int(0.5 * self.eeg_sr):
                    logger.debug(f"Not enough EEG data yet (got {eeg_data.shape[1] if len(eeg_data) > 0 else 0} samples)")
                    self.statusUpdated.emit("Accumulating EEG data...")
                    self.msleep(self.update_speed_ms)
                    continue

                logger.debug(f"Got EEG data with shape {eeg_data.shape}")

                # Pull GYRO data if available
                head_movement = 0
                if self.gyro_channels:
                    try:
                        gyro_data = self.board_shim.get_current_board_data(
                            int(self.power_metric_window_s * self.gyro_sr),
                            self.gyro_preset
                        )

                        if len(gyro_data) > 0 and gyro_data.shape[1] > 0:
                            # Calculate head movement (match original)
                            gyro_slice = gyro_data[:, -int(self.power_metric_window_s * self.gyro_sr):]
                            head_movement = np.clip(np.mean(np.abs(gyro_slice)) / 50, 0, 1)
                            logger.debug(f"GYRO head_movement={head_movement:.3f}")
                    except BrainFlowError as e:
                        if e.exit_code == BrainFlowExitCodes.INVALID_ARGUMENTS_ERROR:
                            pass  # Not critical, just skip GYRO this iteration
                        else:
                            raise e

                # Perform bad channel detection (on the power metric window)
                logger.debug("Detecting bad channels...")
                bad_channels = self._detect_bad_channels(eeg_data)
                logger.info(f"Bad channels detected: {[ch.name for ch in bad_channels]}")

                # Re-reference EEG
                logger.debug(f"Re-referencing EEG (method={self.settings['reference']})")
                eeg_data = self._rereference_eeg(eeg_data, bad_channels)

                # Process EEG and calculate brain metrics
                logger.debug("Calculating brain metrics...")
                avg_bands, engagement_idx, inverse_workload_idx = self._process_eeg(eeg_data, bad_channels)
                logger.debug(f"Bands={[f'{b:.2f}' for b in avg_bands]}, engagement={engagement_idx:.3f}, inverse_workload={inverse_workload_idx:.3f}")

                # Update calibration and history
                num_good_channels = len([ch for ch in self.eeg_channels if not ch.reference and ch not in bad_channels])

                if num_good_channels > 0:
                    # Only use valid scores to scale and calibrate
                    self.engagement_calib.append(engagement_idx)
                    self.inverse_workload_calib.append(inverse_workload_idx)
                else:
                    engagement_idx = 0
                    inverse_workload_idx = 0

                # Limit lengths of history and calib
                if len(self.engagement_calib) > self.calib_length:
                    del self.engagement_calib[0]
                if len(self.engagement_hist) > self.hist_length:
                    del self.engagement_hist[0]
                if len(self.inverse_workload_calib) > self.calib_length:
                    del self.inverse_workload_calib[0]
                if len(self.inverse_workload_hist) > self.hist_length:
                    del self.inverse_workload_hist[0]

                # Scale using z-score
                engagement_z = (engagement_idx - np.mean(self.engagement_calib)) / (np.std(self.engagement_calib) + 1e-9)
                engagement_z /= 2 * self.brain_scale
                engagement_z += self.brain_center
                engagement_z = np.clip(engagement_z, 0.05, 1)
                self.engagement_hist.append(engagement_z)

                inverse_workload_z = (inverse_workload_idx - np.mean(self.inverse_workload_calib)) / (np.std(self.inverse_workload_calib) + 1e-9)
                inverse_workload_z /= 2 * self.brain_scale
                inverse_workload_z += self.brain_center
                inverse_workload_z = np.clip(inverse_workload_z, 0.05, 1)
                self.inverse_workload_hist.append(inverse_workload_z)

                # Weighted mean
                engagement_weighted_mean = self._compute_weighted_mean(self.engagement_hist)
                inverse_workload_weighted_mean = self._compute_weighted_mean(self.inverse_workload_hist)

                self.engagement = engagement_weighted_mean
                self.inverse_workload = inverse_workload_weighted_mean

                # Calculate short-term brainpower (match original)
                short_term_brainpower = np.float32(self.engagement + (1 - head_movement) * self.head_impact)

                # Update longer-term history
                self.longerterm_hist.append(short_term_brainpower)
                if len(self.longerterm_hist) > self.longerterm_length:
                    del self.longerterm_hist[0]

                # Calculate longer-term average
                longer_term_brainpower = np.mean(self.longerterm_hist)

                # Final brainpower (match original)
                final_brainpower = np.float32(max(short_term_brainpower, longer_term_brainpower))

                logger.info(f"Results: short={short_term_brainpower:.3f}, long={longer_term_brainpower:.3f}, final={final_brainpower:.3f}")
                logger.info(f"Bands - Delta:{avg_bands[0]:.1f}, Theta:{avg_bands[1]:.1f}, Alpha:{avg_bands[2]:.1f}, Beta:{avg_bands[3]:.1f}, Gamma:{avg_bands[4]:.1f}")

                # Emit results
                self.analysisUpdated.emit(
                    float(final_brainpower),
                    float(short_term_brainpower),
                    float(longer_term_brainpower),
                    avg_bands
                )

                # Update status periodically
                if len(self.engagement_calib) % 50 == 0:
                    self.statusUpdated.emit(f"Running ({num_good_channels}/{len([ch for ch in self.eeg_channels if not ch.reference])} good channels)")
                    logger.info(f"Calib size={len(self.engagement_calib)}, Good channels={num_good_channels}")

            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                self.statusUpdated.emit(f"Error: {str(e)}")
                self.msleep(100)
                continue

            self.msleep(self.update_speed_ms)

    def _detect_bad_channels(self, eeg_data):
        """Detect bad channels based on line noise and amplitude."""
        bad_channels = []

        def highpass(data, fs, cutoff):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            if normal_cutoff >= 1.0:
                return data
            b, a = butter(1, normal_cutoff, btype='high', analog=False)
            y = filtfilt(b, a, data)
            return y

        def lowpass(data, fs, cutoff):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            if normal_cutoff >= 1.0:
                return data
            b, a = butter(1, normal_cutoff, btype='low', analog=False)
            y = filtfilt(b, a, data)
            return y

        for eeg_channel in self.eeg_channels:
            if eeg_channel.reference:
                continue

            if eeg_channel.ch_number >= eeg_data.shape[0]:
                continue

            # Take the power metric window (last N samples)
            channel_data = eeg_data[eeg_channel.ch_number][-int(self.power_metric_window_s * self.eeg_sr):]

            if len(channel_data) < 100:
                continue

            # Calculate power spectral density using welch
            freq, psd = welch(channel_data, fs=self.eeg_sr, nperseg=min(256, len(channel_data)))

            # Calculate line power
            pow_line = np.mean(psd[(freq > 45) & (freq < 55)])
            threshold_pow_line = 500

            # Applying filters
            filtered_data = highpass(channel_data, self.eeg_sr, 15)
            filtered_data = lowpass(filtered_data, self.eeg_sr, 45)

            # Checking the range
            amplitude_range = np.ptp(filtered_data)
            threshold_amplitude = 350

            # If either threshold exceeded, mark as bad
            if pow_line > threshold_pow_line or amplitude_range > threshold_amplitude or amplitude_range < 5:
                bad_channels.append(eeg_channel)

        return bad_channels

    def _rereference_eeg(self, eeg_data, bad_channels):
        """Re-reference EEG data based on settings (match original)."""
        reference = self.settings["reference"]

        if reference == 'mean':
            # Mean of good EEG channels
            good_eeg_idx = [ch.ch_number for ch in self.eeg_channels if not ch.reference and ch not in bad_channels]
            if len(good_eeg_idx) > 0:
                mean_channels = np.mean(eeg_data[good_eeg_idx], axis=0)
                eeg_channels_idx = [ch.ch_number for ch in self.eeg_channels if not ch.reference]
                for idx in eeg_channels_idx:
                    eeg_data[idx] -= mean_channels
        elif reference == 'ref':
            # Use reference electrodes
            ref_channels_idx = [ch.ch_number for ch in self.eeg_channels if ch.reference]
            eeg_channels_idx = [ch.ch_number for ch in self.eeg_channels if not ch.reference]
            if len(ref_channels_idx) > 0 and len(eeg_channels_idx) > 0:
                mean_reference = np.mean(eeg_data[ref_channels_idx], axis=0)
                for idx in eeg_channels_idx:
                    eeg_data[idx] -= mean_reference

        return eeg_data

    def _process_eeg(self, eeg_data, bad_channels):
        """Process EEG data to extract band powers and brain metrics (match original)."""
        avg_bands = [0, 0, 0, 0, 0]
        inverse_workload_idx = 0
        engagement_idx = 0

        valid_channel_count = 0

        for eeg_channel in self.eeg_channels:
            if eeg_channel.reference or eeg_channel in bad_channels:
                continue

            if eeg_channel.ch_number >= eeg_data.shape[0]:
                continue

            # Take the power metric window (last N samples)
            channel_data = eeg_data[eeg_channel.ch_number][-int(self.power_metric_window_s * self.eeg_sr):].copy()

            if len(channel_data) < 100:
                continue

            # Detrend
            channel_data = channel_data - np.mean(channel_data)

            # Bandpass filter
            b_bp, a_bp = butter(2, [1.0/(self.eeg_sr/2), min(59.0/(self.eeg_sr/2), 0.99)], btype='band')
            channel_data = filtfilt(b_bp, a_bp, channel_data)

            # Bandstop (notch) filter
            if 48.0/(self.eeg_sr/2) < 0.99 and 52.0/(self.eeg_sr/2) < 0.99:
                b_notch, a_notch = butter(2, [48.0/(self.eeg_sr/2), 52.0/(self.eeg_sr/2)], btype='bandstop')
                channel_data = filtfilt(b_notch, a_notch, channel_data)

            # Compute PSD
            if len(channel_data) < self.psd_size:
                nperseg = min(len(channel_data), 256)
            else:
                nperseg = self.psd_size

            freq, psd = welch(channel_data, fs=self.eeg_sr, nperseg=nperseg)

            # Compute band powers (use sum to match BrainFlow's get_band_power)
            def band_power(low, high):
                idx = np.logical_and(freq >= low, freq <= high)
                return np.sum(psd[idx]) if np.any(idx) else 0.0

            delta = band_power(1.0, 4.0)
            theta = band_power(4.0, 8.0)
            alpha = band_power(8.0, 13.0)
            beta = band_power(13.0, 30.0)
            gamma = band_power(30.0, 60.0)

            avg_bands[0] += delta
            avg_bands[1] += theta
            avg_bands[2] += alpha
            avg_bands[3] += beta
            avg_bands[4] += gamma

            # Compute brain metrics (match original formulas)
            if (theta + alpha) > 0 and gamma > 0:
                engagement_idx += (beta / (theta + alpha)) / gamma
                inverse_workload_idx += (alpha / theta) / gamma if theta > 0 else 0

            valid_channel_count += 1

        # Average the bands and metrics
        if valid_channel_count > 0:
            avg_bands = [x / valid_channel_count for x in avg_bands]
            engagement_idx = engagement_idx / valid_channel_count
            inverse_workload_idx = inverse_workload_idx / valid_channel_count
        else:
            avg_bands = [0, 0, 0, 0, 0]
            engagement_idx = 0
            inverse_workload_idx = 0

        return avg_bands, engagement_idx, inverse_workload_idx

    def _compute_weighted_mean(self, hist):
        """Compute weighted mean with weights increasing linearly."""
        weighted_sum = 0
        sumweight = 0
        for count, hist_val in enumerate(hist):
            weighted_sum += hist_val * count
            sumweight += count
        return weighted_sum / sumweight if sumweight > 0 else 0

    def stop(self):
        """Stop the worker thread."""
        self._running = False
        self.quit()
        self.wait()
