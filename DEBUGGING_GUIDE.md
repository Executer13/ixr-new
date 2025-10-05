# Debugging Guide for LSL Stream Discovery Issue

## Problem
The Plot tab shows "No stream found" even after the Muse sensor is connected, while the Analysis tab can access the board data directly.

## What to Check

### 1. After Connecting Muse Sensor

Look for these debug messages in order:

```
[DEBUG] start_stream called. connected=True
[DEBUG] handler=<...>, handler.board=<BoardShim object>
[DEBUG] Creating NEW LSL publisher...
[DEBUG] About to create BrainFlowLSLPublisher with board_shim=<BoardShim object>
Creating persistent LSL outlet for ixr-suite-eeg-data with X channels at Y Hz
Persistent LSL outlet created for eeg (name: ixr-suite-eeg-data)
Creating persistent LSL outlet for ixr-suite-gyro-data with X channels at Y Hz
Persistent LSL outlet created for gyro (name: ixr-suite-gyro-data)
[DEBUG] BrainFlowLSLPublisher created, starting thread...
[DEBUG] LSL publisher thread started.
LSL stream started.
```

### 2. When LSL Publisher Starts Running

```
[LSL_PUBLISHER DEBUG] run() method started, entering main loop...
[LSL_PUBLISHER DEBUG] Loop iteration 0, streaming_enabled=True
```

### 3. When Clicking "Refresh Streams" in Sensors Tab

```
get_available_streams
Found X LSL stream(s)
  - ixr-suite-eeg-data (EEG) - 4 channels
  - ixr-suite-gyro-data (GYRO) - 6 channels
```

### 4. When Double-Clicking a Stream to Add to Plot

```
[DASHBOARD DEBUG] on_add_stream called for: ixr-suite-eeg-data
[PLOT_TAB DEBUG] add_stream called for: ixr-suite-eeg-data
[PLOT_TAB DEBUG] Stream type: EEG, channels: 4
[PLOT_TAB DEBUG] Creating StreamInlet for ixr-suite-eeg-data...
```

## Common Issues

### Issue 1: LSL Publisher Not Created
**Symptom**: Don't see "Creating NEW LSL publisher..." message
**Cause**: `start_stream()` not being called
**Solution**: Check if Muse connection triggers `start_stream()`

### Issue 2: LSL Outlets Not Created
**Symptom**: Don't see "Creating persistent LSL outlet..." messages
**Cause**: Error in BrainFlowLSLPublisher.__init__()
**Solution**: Check for exceptions during outlet creation

### Issue 3: Streams Not Discovered
**Symptom**: "Found 0 LSL stream(s)" when refreshing
**Cause**: LSL outlets not advertising properly OR network issue
**Solution**: Check if outlets were created, verify multicast working

### Issue 4: Board Not Prepared
**Symptom**: See "Board not prepared yet..." repeatedly
**Cause**: BrainFlow board session not ready
**Solution**: Wait longer after connection, check board preparation

## Testing Steps

1. Start application
2. Click "Connect Muse"
3. Wait for "Connected" status
4. Check console for debug messages from steps 1-2 above
5. Click "Refresh Streams" in Sensors tab
6. Check console for messages from step 3 above
7. If streams found, double-click to add to Plot tab
8. Check console for messages from step 4 above
9. Switch to Plot tab to see data visualization

## Test Script

Use `test_lsl_discovery.py` to verify LSL streams independently:
```bash
python test_lsl_discovery.py
```

This should show all available LSL streams on the network.
