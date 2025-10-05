# modern_theme.py
"""
Modern gradient theme inspired by smart home dashboards.
Beautiful gradients, card layouts, and excellent visibility.
"""

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
import pyqtgraph as pg


class ModernTheme:
    """Modern gradient theme configuration."""

    # Color Palette - Clean White Theme
    COLORS = {
        # Backgrounds - White theme
        'bg_primary': '#FFFFFF',
        'bg_secondary': '#F8F9FA',
        'bg_tertiary': '#F1F3F5',

        # Card Backgrounds
        'card_bg': '#FFFFFF',
        'card_bg_solid': '#FFFFFF',
        'card_hover': '#F8F9FA',

        # Surfaces
        'surface': '#F8F9FA',
        'surface_elevated': '#FFFFFF',

        # Accents
        'accent_purple': '#7c3aed',
        'accent_pink': '#ec4899',
        'accent_blue': '#2563eb',
        'accent_cyan': '#0891b2',

        # Status Colors
        'success': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6',

        # Text Colors
        'text_primary': '#1f2937',
        'text_secondary': '#6b7280',
        'text_tertiary': '#9ca3af',

        # Plot Colors - White background with dark elements
        'plot_bg': '#FFFFFF',
        'plot_card_bg': '#FFFFFF',
        'plot_fg': '#1f2937',
        'plot_grid': '#e5e7eb',
        'plot_axis': '#6b7280',

        # EEG Colors (modern professional palette for data visualization)
        'eeg_1': '#3b82f6',  # Delta - Blue
        'eeg_2': '#06b6d4',  # Theta - Cyan
        'eeg_3': "#1810b9",  # Alpha - Green
        'eeg_4': "#800bf5",  # Beta - Amber
        'eeg_5': '#8b5cf6',  # Gamma - Purple
        'eeg_6': "#05335f",  # Teal
        'eeg_7': "#046e67",  # Yellow
        'eeg_8': "#4321ed",  # Red
    }

    @staticmethod
    def apply_pyqtgraph_theme():
        """Apply modern theme to PyQtGraph plots."""
        pg.setConfigOption('background', ModernTheme.COLORS['plot_bg'])
        pg.setConfigOption('foreground', ModernTheme.COLORS['plot_fg'])
        # CRITICAL PERFORMANCE: Disable antialiasing (OpenGL handles smoothing)
        pg.setConfigOption('antialias', False)
        # Performance: Ensure OpenGL is enabled for hardware acceleration
        pg.setConfigOption('useOpenGL', True)
        # Performance: Disable unnecessary cleanup on exit
        pg.setConfigOption('exitCleanup', False)

    @staticmethod
    def get_gradient(color1, color2, color3=None, orientation='vertical'):
        """Generate CSS gradient string."""
        if color3:
            if orientation == 'vertical':
                return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {color1}, stop:0.5 {color2}, stop:1 {color3})"
            else:  # horizontal
                return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:0.5 {color2}, stop:1 {color3})"
        else:
            if orientation == 'vertical':
                return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {color1}, stop:1 {color2})"
            else:  # horizontal
                return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2})"

    @staticmethod
    def get_main_gradient():
        """Get the main background gradient - subtle white to light gray."""
        return ModernTheme.get_gradient(
            ModernTheme.COLORS['bg_primary'],
            ModernTheme.COLORS['bg_secondary'],
            ModernTheme.COLORS['bg_tertiary']
        )

    @staticmethod
    def create_glow_effect(color, blur_radius=20):
        """Create a glow effect for widgets."""
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(blur_radius)
        glow.setColor(QColor(color))
        glow.setOffset(0, 0)
        return glow

    @staticmethod
    def create_depth_shadow(elevation='medium'):
        """Create depth shadow for 3D effect."""
        shadow = QGraphicsDropShadowEffect()

        if elevation == 'low':
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 60))
        elif elevation == 'medium':
            shadow.setBlurRadius(15)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 80))
        elif elevation == 'high':
            shadow.setBlurRadius(25)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 100))

        return shadow

    @staticmethod
    def get_button_style(variant='primary'):
        """Get button stylesheet with modern styling and proper text contrast."""
        base_style = """
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
                {background}
                color: {color};
            }}
            QPushButton:hover {{
                {hover_background}
                color: {hover_color};
            }}
            QPushButton:pressed {{
                {pressed_background}
                color: {pressed_color};
            }}
            QPushButton:disabled {{
                background: {disabled_bg};
                color: {disabled_color};
            }}
        """

        if variant == 'primary':
            return base_style.format(
                background=f"background: {ModernTheme.COLORS['accent_blue']};",
                color="#FFFFFF",  # White text on blue background
                hover_background=f"background: #1d4ed8;",
                hover_color="#FFFFFF",
                pressed_background=f"background: #1e40af;",
                pressed_color="#FFFFFF",
                disabled_bg=ModernTheme.COLORS['bg_tertiary'],
                disabled_color=ModernTheme.COLORS['text_tertiary']
            )
        elif variant == 'danger':
            return base_style.format(
                background=f"background: {ModernTheme.COLORS['danger']};",
                color="#FFFFFF",  # White text on red background
                hover_background="background: #dc2626;",
                hover_color="#FFFFFF",
                pressed_background="background: #b91c1c;",
                pressed_color="#FFFFFF",
                disabled_bg=ModernTheme.COLORS['bg_tertiary'],
                disabled_color=ModernTheme.COLORS['text_tertiary']
            )
        elif variant == 'success':
            return base_style.format(
                background=f"background: {ModernTheme.COLORS['success']};",
                color="#FFFFFF",  # White text on green background
                hover_background="background: #059669;",
                hover_color="#FFFFFF",
                pressed_background="background: #047857;",
                pressed_color="#FFFFFF",
                disabled_bg=ModernTheme.COLORS['bg_tertiary'],
                disabled_color=ModernTheme.COLORS['text_tertiary']
            )
        elif variant == 'secondary':
            # Add border for secondary buttons
            return f"""
            QPushButton {{
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
                background: {ModernTheme.COLORS['bg_primary']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background: {ModernTheme.COLORS['bg_secondary']};
                border: 1px solid {ModernTheme.COLORS['text_tertiary']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background: {ModernTheme.COLORS['bg_tertiary']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
            QPushButton:disabled {{
                background: {ModernTheme.COLORS['bg_tertiary']};
                color: {ModernTheme.COLORS['text_tertiary']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
            }}
        """

    @staticmethod
    def get_tab_widget_style():
        """Get tab widget stylesheet - clean white theme."""
        return f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {ModernTheme.COLORS['bg_tertiary']};
                color: {ModernTheme.COLORS['text_secondary']};
                padding: 12px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-bottom: none;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
                min-width: 80px;
            }}
            QTabBar::tab:selected {{
                background: {ModernTheme.COLORS['bg_primary']};
                color: {ModernTheme.COLORS['text_primary']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-bottom: 3px solid {ModernTheme.COLORS['accent_blue']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {ModernTheme.COLORS['bg_secondary']};
                color: {ModernTheme.COLORS['text_primary']};
            }}
        """

    @staticmethod
    def get_widget_style():
        """Get general widget background style with gradient."""
        return f"""
            QWidget {{
                background: {ModernTheme.get_main_gradient()};
                color: {ModernTheme.COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
        """

    @staticmethod
    def get_card_style():
        """Get card/container style - white with elevation shadow (no border)."""
        # Use direct selector (>) to only style the card itself, not children like PlotWidget
        return f"""
            QWidget {{
                background: {ModernTheme.COLORS['card_bg']};
                border: none;
                border-radius: 12px;
                color: {ModernTheme.COLORS['text_primary']};
            }}
            QWidget > QWidget {{
                background: transparent;
            }}
        """

    @staticmethod
    def get_label_style(variant='primary'):
        """Get label stylesheet."""
        if variant == 'primary':
            return f"""
                QLabel {{
                    color: {ModernTheme.COLORS['text_primary']};
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }}
            """
        elif variant == 'secondary':
            return f"""
                QLabel {{
                    color: {ModernTheme.COLORS['text_secondary']};
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }}
            """
        elif variant == 'title':
            return f"""
                QLabel {{
                    color: {ModernTheme.COLORS['text_primary']};
                    font-size: 18px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
            """

    @staticmethod
    def get_spinbox_style():
        """Get spinbox stylesheet."""
        return f"""
            QDoubleSpinBox, QSpinBox {{
                background: {ModernTheme.COLORS['surface']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
            }}
            QDoubleSpinBox:hover, QSpinBox:hover {{
                border: 1px solid {ModernTheme.COLORS['accent_cyan']};
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {ModernTheme.COLORS['accent_cyan']};
                outline: none;
            }}
            QDoubleSpinBox::up-button, QSpinBox::up-button {{
                background: transparent;
                border: none;
                border-top-right-radius: 8px;
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                height: 50%;
            }}
            QDoubleSpinBox::down-button, QSpinBox::down-button {{
                background: transparent;
                border: none;
                border-bottom-right-radius: 8px;
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                height: 50%;
            }}
            QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-bottom: 8px solid {ModernTheme.COLORS['text_primary']};
            }}
            QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid {ModernTheme.COLORS['text_primary']};
            }}
            QDoubleSpinBox::up-arrow:hover, QSpinBox::up-arrow:hover {{
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-bottom: 8px solid {ModernTheme.COLORS['accent_cyan']};
            }}
            QDoubleSpinBox::down-arrow:hover, QSpinBox::down-arrow:hover {{
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid {ModernTheme.COLORS['accent_cyan']};
            }}
        """

    @staticmethod
    def get_checkbox_style():
        """Get checkbox stylesheet."""
        return f"""
            QCheckBox {{
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid {ModernTheme.COLORS['text_secondary']};
                background: {ModernTheme.COLORS['surface']};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {ModernTheme.COLORS['accent_cyan']};
            }}
            QCheckBox::indicator:checked {{
                background: {ModernTheme.COLORS['accent_cyan']};
                border: 2px solid {ModernTheme.COLORS['accent_cyan']};
            }}
        """

    @staticmethod
    def get_textedit_style():
        """Get text edit stylesheet - white background."""
        return f"""
            QTextEdit {{
                background: {ModernTheme.COLORS['bg_primary']};
                border: 1px solid {ModernTheme.COLORS['plot_grid']};
                border-radius: 8px;
                padding: 12px;
                color: {ModernTheme.COLORS['text_primary']};
                font-size: 12px;
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            }}
        """

    @staticmethod
    def get_scrollarea_style():
        """Get scroll area stylesheet."""
        return f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {ModernTheme.COLORS['surface']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {ModernTheme.COLORS['text_tertiary']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ModernTheme.COLORS['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """

    @staticmethod
    def get_plot_widget_style():
        """Get PyQtGraph PlotWidget modern styling."""
        return {
            'background': ModernTheme.COLORS['plot_bg'],
            'foreground': ModernTheme.COLORS['plot_fg'],
            'border': f"1px solid rgba(255, 255, 255, 0.1)",
            'border-radius': '12px',
        }

    @staticmethod
    def style_plot_widget(plot_widget):
        """Apply modern styling to a PlotWidget - clean white theme."""
        # Set background to white
        plot_widget.setBackground(ModernTheme.COLORS['plot_bg'])

        # Get the ViewBox and set background
        vb = plot_widget.getViewBox()
        if vb is not None:
            vb.setBackgroundColor(ModernTheme.COLORS['plot_bg'])

        # Style axes with dark text for white background
        for axis in ['left', 'bottom', 'right', 'top']:
            ax = plot_widget.getAxis(axis)
            ax.setPen(pg.mkPen(color=ModernTheme.COLORS['plot_axis'], width=2))
            ax.setTextPen(pg.mkPen(color=ModernTheme.COLORS['text_primary']))

        # Add visible grid on white background
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Note: Do NOT apply QWidget stylesheet here as it conflicts with PyQtGraph rendering
        # PyQtGraph uses internal OpenGL/QPainter rendering which doesn't work well with CSS
        # The card container provides the border and styling instead
