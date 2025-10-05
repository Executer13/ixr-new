# Stream Discovery Fix - Plot Tab

## Issue
After optimization removed auto-discovery on tab switch, the Plot tab had no way to detect and add LSL streams, making it impossible to visualize sensor data.

## Solution Implemented

### **"Discover Streams" Button in Plot Tab**

Added a smart, user-triggered discovery system that combines the best of both worlds:
- **Performance**: No automatic discovery (no lag on tab switching)
- **Convenience**: One-click discovery and auto-add of sensor streams

### Architecture

```
User clicks "Discover Streams" in Plot Tab
          ↓
Plot Tab emits signal → Dashboard receives it
          ↓
Dashboard starts async LSL discovery (non-blocking)
          ↓
Background thread resolves LSL streams (0.5s)
          ↓
Callback receives streams → Auto-adds sensor streams
          ↓
Updates LSL Browser UI highlighting
```

### Components Modified

#### 1. **LSL Browser Widget** (`gui/lsl_browser_widget.py`)
- **New Method**: `async_refresh_streams()` - Non-blocking stream discovery
- **New Method**: `_on_async_streams_discovered()` - Callback for async results
- **Refactored**: `_populate_stream_list()` - Extracted list population logic

**Key Changes:**
```python
def async_refresh_streams(self):
    """Asynchronously refresh streams (non-blocking)."""
    self.lsl_fetcher.get_available_streams_async(
        callback=self._on_async_streams_discovered,
        wait_time=0.5
    )
```

#### 2. **Plot Tab** (`gui/plot_tab.py`)
- **New UI**: "Discover Streams" button with primary styling and tooltip
- **New Signal**: `discover_streams_requested` - Emitted when button clicked
- **New Method**: `on_discover_streams()` - Button click handler

**Key Changes:**
```python
self.discover_button = QPushButton("Discover Streams")
self.discover_button.setStyleSheet(ModernTheme.get_button_style('primary'))
self.discover_button.setToolTip("Auto-discover and add available LSL streams to plot")
self.discover_button.clicked.connect(self.on_discover_streams)
```

#### 3. **Dashboard** (`gui/dashboard.py`)
- **New Connection**: Plot tab's discover signal → dashboard handler
- **New Method**: `on_discover_streams_from_plot()` - Initiates async discovery
- **New Method**: `_on_streams_discovered_for_plot()` - Auto-adds sensor streams

**Key Changes:**
```python
def _on_streams_discovered_for_plot(self, streams):
    """Auto-add sensor streams to plot after discovery."""
    # Smart filtering: only add EEG, ECG, PPG, GYRO, Accelerometer streams
    # Checks if stream already plotted to avoid duplicates
    # Updates UI highlighting in LSL browser
```

### User Workflow

#### **Method 1: Plot Tab Discovery (Recommended)**
1. Go to Plot tab
2. Click "Discover Streams" button
3. Streams are automatically discovered and added (async, ~0.5s)
4. Start visualizing immediately

#### **Method 2: Sensors Tab Manual Add**
1. Go to Sensors tab
2. Click "Refresh Streams"
3. Double-click desired streams (or right-click → "Add to Plot")
4. Switch to Plot tab to visualize

### Features

#### Smart Auto-Add Logic
Only auto-adds streams that are:
- ✅ Sensor streams (EEG, ECG, PPG, GYRO, Accelerometer)
- ✅ Muse or Polar branded streams
- ✅ Not already being plotted (prevents duplicates)

#### Performance Benefits
- **Non-Blocking**: Async discovery doesn't freeze UI
- **Cached**: 2-second cache reduces redundant LSL queries
- **Fast**: 0.5s discovery timeout (down from 1.0s)
- **No Auto-Discovery**: Only runs when user clicks button

#### User Experience
- **One-Click**: Single button press discovers and adds all sensor streams
- **Visual Feedback**: Log messages show discovery progress
- **Clear Tooltip**: "Auto-discover and add available LSL streams to plot"
- **Consistent**: Works with existing LSL browser highlighting

### Stream Filtering Logic

The system auto-adds streams matching these criteria:

```python
is_sensor_stream = (
    "Muse" in stream_name or
    "Polar" in stream_name or
    stream_type in ["EEG", "ECG", "PPG", "GYRO", "Accelerometer"]
)
```

This ensures only relevant physiological data streams are added, not system or debug streams.

### Testing Results

✅ **All tests passed:**
- Imports verified successfully
- Async methods available
- Application starts without errors
- Button appears in Plot tab UI
- Signal connections established
- Async discovery functional

### Files Changed

1. **gui/lsl_browser_widget.py** - Added async refresh capability
2. **gui/plot_tab.py** - Added discover button and signal
3. **gui/dashboard.py** - Added discovery handlers and auto-add logic
4. **sensors/lsl_fetcher.py** - Already had async discovery (from previous optimization)

### Migration from Previous Behavior

**Before (Auto-Discovery on Tab Switch):**
- ❌ Caused 1+ second lag when switching tabs
- ❌ Ran discovery even when not needed
- ❌ Blocked UI thread during discovery
- ✅ Automatic (no user action required)

**After (Manual Discovery Button):**
- ✅ No lag on tab switching
- ✅ Discovery only when needed
- ✅ Non-blocking async discovery
- ✅ Still convenient (one button click)

### Best Practices Applied

1. **User Control**: Discovery only happens when user wants it
2. **Non-Blocking**: Async thread prevents UI freeze
3. **Smart Defaults**: Auto-adds only relevant sensor streams
4. **Performance**: Cached results, fast timeout, no polling
5. **Feedback**: Log messages inform user of progress

### Future Enhancements

Potential improvements:
- **Auto-refresh on sensor connect**: Trigger discovery when Muse/Polar connects
- **Periodic polling option**: Optional timer-based discovery (user-configurable)
- **Stream templates**: Save/load preferred stream configurations
- **Bulk actions**: Select multiple streams to add at once

---

**Status**: ✅ Implemented and Tested
**Performance Impact**: Positive (eliminated tab switching lag, maintained convenience)
**User Impact**: Minimal (one extra click, faster overall experience)
