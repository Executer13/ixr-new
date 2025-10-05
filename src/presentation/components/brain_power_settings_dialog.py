"""
Brain Power Settings Dialog - Presentation component for configuring brain power analysis.

This dialog allows users to configure parameters for brain power analysis,
based on the original IXR Suite parameters.
"""

from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                             QComboBox, QSpinBox, QVBoxLayout, QLabel)
from PyQt5.QtCore import Qt
from gui.modern_theme import ModernTheme


class BrainPowerSettingsDialog(QDialog):
    """
    Popup dialog to configure Brain Power Analysis settings.
    Based on the original IXR Suite parameters.
    """
    def __init__(self, parent=None, default_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Brain Power Analysis Settings")
        self.setMinimumWidth(520)

        self.default_settings = default_settings or {
            "calib_length": 600,        # seconds
            "power_length": 10,          # seconds
            "scale": 1.5,               # Match original IXR-Suite
            "offset": 0.5,              # center - Match original IXR-Suite
            "head_impact": 0.2,
            "longerterm_length": 30,    # seconds
            "reference": "mean"         # Match original IXR-Suite (mean referencing)
        }

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Apply modern theme
        self.setStyleSheet(f"""
            QDialog {{
                background: {ModernTheme.COLORS['bg_primary']};
            }}
            QLabel {{
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        # Title section
        title_label = QLabel("Configure Analysis Parameters")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {ModernTheme.COLORS['text_primary']};
            letter-spacing: -0.3px;
            padding-bottom: 8px;
        """)
        main_layout.addWidget(title_label)

        # Form layout with consistent spacing
        layout = QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setHorizontalSpacing(16)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Calibration history length
        self.calib_spin = QSpinBox()
        self.calib_spin.setRange(60, 3600)
        self.calib_spin.setValue(self.default_settings["calib_length"])
        self.calib_spin.setSuffix(" s")
        self.calib_spin.setMinimumWidth(150)
        self.calib_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.calib_spin.setToolTip("Duration of the rolling calibration in seconds (default = 600)")
        layout.addRow("Calibration History:", self.calib_spin)

        # Power history length
        self.power_spin = QSpinBox()
        self.power_spin.setRange(1, 60)
        self.power_spin.setValue(self.default_settings["power_length"])
        self.power_spin.setSuffix(" s")
        self.power_spin.setMinimumWidth(150)
        self.power_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.power_spin.setToolTip("Duration of the current brain power measurement in seconds (default = 10)")
        layout.addRow("Power History:", self.power_spin)

        # Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0)
        self.scale_spin.setValue(self.default_settings["scale"])
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setMinimumWidth(150)
        self.scale_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.scale_spin.setToolTip("Adjusts the scale of the BCI. SMALLER values make it EASIER to reach maximum and minimum (recommended between 0.7 and 1.3, default = 1.5)")
        layout.addRow("Scale:", self.scale_spin)

        # Center (offset)
        self.center_spin = QDoubleSpinBox()
        self.center_spin.setRange(0.0, 1.0)
        self.center_spin.setValue(self.default_settings["offset"])
        self.center_spin.setSingleStep(0.05)
        self.center_spin.setMinimumWidth(150)
        self.center_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.center_spin.setToolTip("The value around which the brainpower should be centered. If at 0.5 then your 'normal' brain power is 0.5 (default = 0.5)")
        layout.addRow("Center:", self.center_spin)

        # Head impact strength
        self.head_impact_spin = QDoubleSpinBox()
        self.head_impact_spin.setRange(0.0, 1.0)
        self.head_impact_spin.setValue(self.default_settings["head_impact"])
        self.head_impact_spin.setSingleStep(0.05)
        self.head_impact_spin.setMinimumWidth(150)
        self.head_impact_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.head_impact_spin.setToolTip("The amount of impact the head movement can have on the brain power (default = 0.2)")
        layout.addRow("Head Impact:", self.head_impact_spin)

        # Longerterm average length
        self.longerterm_spin = QSpinBox()
        self.longerterm_spin.setRange(5, 300)
        self.longerterm_spin.setValue(self.default_settings["longerterm_length"])
        self.longerterm_spin.setSuffix(" s")
        self.longerterm_spin.setMinimumWidth(150)
        self.longerterm_spin.setStyleSheet(ModernTheme.get_spinbox_style())
        self.longerterm_spin.setToolTip("Duration of the longer-term average in seconds (default = 30)")
        layout.addRow("Long-term Average:", self.longerterm_spin)

        # Reference method
        self.reference_combo = QComboBox()
        self.reference_combo.addItems(["none", "mean", "ref"])
        self.reference_combo.setMinimumWidth(150)
        self.reference_combo.setStyleSheet(f"""
            QComboBox {{
                background: {ModernTheme.COLORS['surface']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox:hover {{
                border: 1px solid {ModernTheme.COLORS['accent_cyan']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: {ModernTheme.COLORS['bg_primary']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                selection-background-color: {ModernTheme.COLORS['accent_cyan']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
        """)
        current_ref = self.default_settings["reference"]
        index = self.reference_combo.findText(current_ref)
        if index >= 0:
            self.reference_combo.setCurrentIndex(index)
        self.reference_combo.setToolTip("Determines what type of re-reference to use:\n"
                                        "- none: No re-referencing is applied\n"
                                        "- mean (default): Use the mean of the four frontal and temporal electrodes\n"
                                        "- ref: Use the reference electrode(s) as a reference")
        layout.addRow("Reference Method:", self.reference_combo)

        main_layout.addLayout(layout)
        main_layout.addSpacing(12)

        # OK/Cancel buttons with modern styling
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.button(QDialogButtonBox.Ok).setStyleSheet(ModernTheme.get_button_style('primary'))
        self.buttonBox.button(QDialogButtonBox.Cancel).setStyleSheet(ModernTheme.get_button_style('secondary'))
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        main_layout.addWidget(self.buttonBox)

    def get_settings(self):
        """Return current settings as a dictionary."""
        return {
            "calib_length": self.calib_spin.value(),
            "power_length": self.power_spin.value(),
            "scale": self.scale_spin.value(),
            "offset": self.center_spin.value(),
            "head_impact": self.head_impact_spin.value(),
            "longerterm_length": self.longerterm_spin.value(),
            "reference": self.reference_combo.currentText()
        }
