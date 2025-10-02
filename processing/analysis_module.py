# analysis_module.py
from PyQt5.QtWidgets import QWidget

class AnalysisModule(QWidget):
    """
    Base class for all analysis modules.
    Provides a common API for creating the settings UI, processing data, and updating display.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def setup_ui(self):
        """Initialize the analysis UI. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def update_analysis(self, data):
        """Process new data (e.g., LSL chunk) and update the display.
           'data' might be a dictionary of stream data.
        """
        raise NotImplementedError("Subclasses must implement update_analysis()")
    
    def get_settings(self):
        """Return current settings as a dictionary."""
        raise NotImplementedError("Subclasses must implement get_settings()")
    
    def set_settings(self, settings):
        """Apply settings from a dictionary."""
        raise NotImplementedError("Subclasses must implement set_settings()")
