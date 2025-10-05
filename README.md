# IXR EEG Suite

A cross-platform Brain-Computer Interface (BCI) application for real-time EEG data acquisition, streaming, and cognitive analysis from Muse and Polar sensors.

## Overview

IXR EEG Suite is a professional-grade biosignal processing platform that enables researchers and developers to:
- Connect to commercial EEG headsets (Muse S) and physiological sensors (Polar H10)
- Stream real-time biosignal data using Lab Streaming Layer (LSL) protocol
- Process and analyze EEG signals with advanced signal processing techniques
- Visualize brain activity patterns with modern, intuitive interfaces
- Perform cognitive state analysis with head movement compensation

## Key Features

### Sensor Support
- **Muse S EEG Headset** - 4-channel EEG with gyroscope data
- **Polar H10** - Heart rate and physiological monitoring
- Bluetooth Low Energy (BLE) connectivity
- Cross-platform sensor discovery and connection

### Real-Time Data Streaming
- Lab Streaming Layer (LSL) integration
- Multi-stream synchronization (EEG + GYRO)
- Network-based data distribution
- Stream browser for discovery and monitoring

### Signal Processing
- BrainFlow-based preprocessing pipeline
- Bandpass filtering (configurable frequency ranges)
- Notch filtering (50/60 Hz line noise removal)
- Power Spectral Density (PSD) computation
- EEG band extraction (Delta, Theta, Alpha, Beta, Gamma)
- Bad channel detection and removal
- Common average re-referencing

### Brain Power Analysis
- Real-time cognitive state monitoring
- Head movement compensation using gyroscope data
- Calibration-based normalization
- Channel-specific and global metrics
- Temporal smoothing for stable readings

### Modern GUI
- PyQt5-based dashboard with Apple-inspired design
- Real-time time-series plotting (pyqtgraph)
- PSD and band power visualizations
- LSL stream browser
- Sensor status indicators with live updates

## Architecture

Built with **Clean Architecture** principles:

```
src/
├── presentation/       # UI components (PyQt5)
├── application/        # Services & business logic
├── domain/            # Interfaces & domain models
├── infrastructure/    # Hardware adapters (sensors, LSL)
└── common/            # Utilities, constants, config
```

**Design Patterns Implemented:**
- Factory Pattern (SensorFactory)
- Adapter Pattern (Sensor adapters)
- Dependency Injection (ServiceContainer)
- Service Layer Pattern
- Observer/Event Bus
- Repository Pattern

## Prerequisites

- **Python**: 3.8 or higher
- **Operating System**:
  - Windows 10+ (64-bit recommended)
  - macOS 10.13+ (High Sierra or later)
  - Linux (Ubuntu 20.04+ or equivalent)
- **Bluetooth**: BLE-capable Bluetooth adapter
- **Hardware** (optional):
  - Muse S EEG headset
  - Polar H10 heart rate monitor

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd IXR-new
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### Platform-Specific Setup

#### Windows
- Install Visual C++ Redistributable if needed
- Ensure Bluetooth adapter is enabled in Device Manager
- Allow Python through Windows Firewall for LSL networking

#### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Grant Bluetooth permissions in System Preferences > Security & Privacy
```

#### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip bluez
sudo apt-get install python3-pyqt5 libxcb-xinerama0
sudo apt-get install mesa-utils libgl1-mesa-glx

# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER
```

## Usage

### Start the Application
```bash
python main.py
```

### Basic Workflow

1. **Connect Sensors**
   - Navigate to the "Sensors" tab
   - Click "Connect Muse" or "Connect Polar"
   - Wait for connection indicator to turn green

2. **Browse LSL Streams**
   - Go to "LSL Streams" tab
   - Click "Discover Streams" to find available data streams
   - View stream metadata and connectivity

3. **Real-Time Plotting**
   - Switch to "Plots" tab
   - Select stream from dropdown
   - View live time-series data and PSD

4. **Brain Power Analysis**
   - Go to "Brain Power" tab
   - Click "Start Analysis" to begin cognitive monitoring
   - Observe real-time metrics with head movement compensation
   - Adjust calibration and power windows as needed

### Configuration

Edit settings in `src/common/config/app_config.py`:
- Logging levels and output
- Analysis parameters
- Signal processing settings
- UI preferences

## Project Structure

```
IXR-new/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── gui/                   # Legacy GUI components
│   ├── dashboard.py       # Main dashboard
│   ├── plot_tab.py        # Plotting interface
│   └── modern_theme.py    # UI styling
├── src/                   # New architecture (Clean Architecture)
│   ├── application/       # Services (SensorService, StreamingService, etc.)
│   ├── domain/           # Interfaces and domain models
│   ├── infrastructure/   # Sensor adapters, LSL, BrainFlow
│   ├── presentation/     # Reusable UI components
│   └── common/           # Utils, constants, logging, DI container
├── IXR-Suite/            # Legacy codebase (being migrated)
└── logs/                 # Application logs (auto-generated)
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| **GUI Framework** | PyQt5 |
| **Plotting** | pyqtgraph, matplotlib |
| **BCI Platform** | BrainFlow |
| **Data Streaming** | Lab Streaming Layer (LSL) |
| **Signal Processing** | NumPy, SciPy |
| **Bluetooth** | bleak (BLE support) |
| **Architecture** | Clean Architecture with DI |

## Development

### Running Tests
```bash
# Test LSL stream discovery
python test_lsl_discovery.py
```

### Logging
Application logs are written to `logs/ixr_suite.log` with automatic rotation.

View logs in real-time:
```bash
tail -f logs/ixr_suite.log
```

### Key Services

**SensorService** - Manages sensor lifecycle and connections
```python
from src.application.services import SensorService
from src.common.utils.service_container import resolve

sensor_service = resolve("SensorService")
sensor = sensor_service.create_sensor(SensorType.MUSE_S, "muse_1")
```

**StreamingService** - Handles LSL operations
```python
from src.application.services import StreamingService

streaming_service = StreamingService()
streams = streaming_service.discover_streams(timeout=2.0)
```

**AnalysisService** - Coordinates cognitive analysis
```python
from src.application.services import AnalysisService

analysis_service = AnalysisService()
analysis_service.start_analysis(settings)
```

## Troubleshooting

### Sensor Connection Issues
- **Bluetooth not found**: Ensure Bluetooth is enabled and BLE is supported
- **Permission denied (Linux)**: Add user to bluetooth group and reboot
- **Connection timeout**: Move sensor closer, ensure it's charged and in pairing mode

### LSL Stream Issues
- **No streams found**: Verify sensor is connected and streaming
- **Firewall blocking**: Allow Python through firewall on Windows
- **Network issues**: LSL uses multicast, ensure network allows it

### Performance Issues
- **Lag in GUI**: Reduce plotting update rate in settings
- **High CPU usage**: Check for runaway threads in logs
- **Memory leaks**: Monitor with `top` or Task Manager

## Documentation

Additional documentation available in the project:
- `EEG_DATA_FLOW.md` - Data flow and processing pipeline details
- `REFACTORING_COMPLETE.md` - Architecture migration notes
- `DEBUGGING_GUIDE.md` - Debugging tips and common issues
- `PERFORMANCE_OPTIMIZATIONS.md` - Performance tuning guide

## Contributing

Contributions are welcome! Please ensure:
- Code follows the Clean Architecture structure
- Type hints are included
- Logging is used instead of print statements
- Changes are tested on multiple platforms

## License

[License information to be added]

## Acknowledgments

- **BrainFlow** - Multi-platform BCI library
- **Lab Streaming Layer** - Real-time data streaming protocol
- **Muse** - Consumer EEG hardware
- **Polar** - Heart rate monitoring technology

---

**Status**: Active development | Core refactoring complete | Ready for testing

For issues and support, please check the documentation files or create an issue in the repository.
