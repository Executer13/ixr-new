# EEG Data Flow - Location Reference

## Overview
This document tracks the exact locations where EEG data is pulled and processed in the Brain Power Analysis system.

---

## 1. LSL Stream Creation (Source)

**File**: `sensors/brainflow_lsl_publisher.py`
**Lines**: 79-112
**Function**: `run()`

```python
# Main LSL publishing loop
data = self.board_shim.get_current_board_data(1024, preset)
```

**Description**:
- BrainFlow board data is pulled from the Muse sensor
- Data is published to LSL streams with names:
  - `ixr-suite-eeg-data` (type: EEG)
  - `ixr-suite-gyro-data` (type: GYRO)

**Location**: This happens in a background thread when Muse is connected

---

## 2. Stream Resolution (Discovery)

**File**: `processing/brain_power_worker.py`
**Lines**: 82-161
**Function**: `resolve_streams()`

```python
# Line 89: Search for EEG streams
eeg_infos = resolve_byprop("type", "EEG", minimum=0, timeout=2)

# Line 98: Search for GYRO streams
gyro_infos = resolve_byprop("type", "GYRO", minimum=0, timeout=2)

# Line 133: Create EEG inlet
self.eeg_inlet = StreamInlet(eeg_infos[0], max_buflen=360)

# Line 152: Create GYRO inlet
self.gyro_inlet = StreamInlet(gyro_infos[0], max_buflen=360)
```

**Description**:
- Searches LSL network for EEG and GYRO streams
- Creates StreamInlet objects to receive data
- Timeout: 2 seconds per stream
- Max retries: 3

**Logs to watch for**:
```
[INFO] RESOLVE_STREAMS: Starting stream resolution...
[INFO] RESOLVE_STREAMS: Found X EEG stream(s)
[INFO] RESOLVE_STREAMS: Found X GYRO stream(s)
```

---

## 3. EEG Data Pull (Main Processing Loop)

**File**: `processing/brain_power_worker.py`
**Lines**: 197-217
**Function**: `run()` - main loop

### **🔴 PRIMARY DATA PULL LOCATION**

```python
# Line 198: Calculate required samples
num_samples = int(self.power_metric_window_s * self.eeg_sr)
# Example: 1.5 seconds * 256 Hz = 384 samples

# Line 202: *** THIS IS WHERE EEG DATA IS PULLED ***
eeg_samples, eeg_timestamps = self.eeg_inlet.pull_chunk(timeout=0.0, max_samples=num_samples*2)

# Line 206: Check if enough data received
if not eeg_timestamps or len(eeg_samples) < num_samples // 4:
    # STUCK HERE if no data!
    self.statusUpdated.emit("Waiting for EEG data...")
    continue
```

**Description**:
- Pulls data from LSL EEG stream via `self.eeg_inlet.pull_chunk()`
- Non-blocking call (timeout=0.0)
- Requests up to 2x required samples (768 samples max)
- Minimum required: 25% of window (96 samples)
- If insufficient data: **CODE GETS STUCK IN THIS LOOP**

**Logs to watch for**:
```
[DEBUG] DATA_PULL: Requesting 384 EEG samples (window=1.5s @ 256.0Hz)
[DEBUG] DATA_PULL: Pulling from EEG inlet at ixr-suite-eeg-data
[DEBUG] DATA_PULL: Received 0 samples, 0 timestamps  ← PROBLEM!
[WARNING] DATA_PULL: Insufficient data! Got 0 samples, need at least 96
```

**Expected when working**:
```
[INFO] DATA_PULL: SUCCESS - Got 384 samples (need 384)
```

---

## 4. GYRO Data Pull

**File**: `processing/brain_power_worker.py`
**Lines**: 219-228
**Function**: `run()` - main loop

```python
# Line 221: Pull GYRO data
gyro_samples, _ = self.gyro_inlet.pull_chunk(timeout=0.0)

# Line 223-226: Calculate head movement
if gyro_samples and len(gyro_samples) > 0:
    gyro_data = np.array(gyro_samples, dtype=float)
    head_movement = np.clip(np.mean(np.abs(gyro_data)) / 50, 0, 1)
```

**Description**:
- Pulls gyroscope data for head movement compensation
- Non-blocking call
- Head movement value ranges from 0 to 1

---

## 5. Data Processing Flow

```
1. Pull EEG chunk     → Line 202 (brain_power_worker.py)
2. Pull GYRO chunk    → Line 221 (brain_power_worker.py)
3. Detect bad channels → Line 232 (_detect_bad_channels)
4. Re-reference       → Line 237 (_rereference_eeg)
5. Extract bands      → Line 241 (_process_eeg)
6. Calculate metrics  → Lines 246-297
7. Emit results       → Line 302 (analysisUpdated signal)
```

---

## Common Issues & Debugging

### Issue: "Waiting for EEG data..." (Code Stuck)

**Root Causes**:
1. **No LSL streams available**
   - Check: `[INFO] RESOLVE_STREAMS: Found 0 EEG stream(s)`
   - Solution: Connect Muse sensor in Sensors tab first

2. **Streams found but not pushing data**
   - Check: `[DEBUG] DATA_PULL: Received 0 samples`
   - Solution: Check if Muse is actually streaming (green indicator)

3. **Insufficient buffer**
   - Check: `[WARNING] DATA_PULL: Insufficient data! Got X samples`
   - Solution: Wait longer for data to accumulate

### How to Check if Data is Flowing

```bash
# Check if LSL streams exist
python -c "from pylsl import resolve_streams; print(len(resolve_streams()), 'streams found')"

# Monitor the logs
tail -f /path/to/log | grep DATA_PULL
```

### Expected Timing
- Stream resolution: ~4 seconds (2s per stream)
- Initial data accumulation: ~2-3 seconds
- Processing loop: Every 50ms (20 Hz)

---

## Data Requirements

| Parameter | Value | Notes |
|-----------|-------|-------|
| Power window | 1.5 seconds | Configurable |
| EEG sample rate | 256 Hz | From Muse S |
| GYRO sample rate | 52 Hz | From Muse S |
| Samples per window | 384 (EEG) | 1.5s × 256Hz |
| Minimum samples | 96 (25%) | To start processing |
| Update rate | 50ms (20 Hz) | Real-time updates |

---

## Key Files Summary

1. **brainflow_lsl_publisher.py** - Creates LSL streams from Muse
2. **brain_power_worker.py** - Consumes LSL streams for analysis
   - `resolve_streams()` - Line 82-161
   - `run()` main loop - Line 180-320
   - **Primary data pull** - Line 202 ⭐

---

## Quick Debug Commands

```bash
# Run with full logging
python main.py 2>&1 | tee brain_power.log

# Filter for important logs only
python main.py 2>&1 | grep -E "(RESOLVE_STREAMS|DATA_PULL|ERROR)"

# Check LSL streams
python -c "from pylsl import resolve_streams; streams = resolve_streams(); [print(s.name(), s.type()) for s in streams]"
```
