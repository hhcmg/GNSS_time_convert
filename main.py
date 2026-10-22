import os
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtGui import QFont, QFontDatabase
from src.qtTimeTool import TimeToolWidget


def _resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _setup_ui_style(app):
    # Use a cross-platform Qt style to reduce OS-native differences.
    app.setStyle(QStyleFactory.create("Fusion"))


def _setup_ui_font(app):
    # Prefer common cross-platform desktop fonts first.
    available = set(QFontDatabase().families())
    for family in ["Segoe UI", "Arial", "Liberation Sans", "Noto Sans", "Helvetica Neue", "DejaVu Sans"]:
        if family in available:
            app.setFont(QFont(family, 11))
            return

    # Final fallback: bundled DejaVu Sans.
    bundled_font = _resource_path("assets", "fonts", "DejaVuSans.ttf")
    if os.path.isfile(bundled_font):
        font_id = QFontDatabase.addApplicationFont(bundled_font)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                app.setFont(QFont(families[0], 11))
                return

    app.setFont(QFont("", 11))


def main():
    # High-DPI: must be configured BEFORE the QApplication is created so the UI
    # rescales correctly across monitors with different scaling factors (e.g. a
    # 150% laptop panel vs a 100% external display). This is what prevents the
    # clipped / squeezed text seen when moving the window between screens.
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except Exception:
            pass
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    _setup_ui_style(app)
    _setup_ui_font(app)
    win = TimeToolWidget(chinese=False)
    win.setWindowTitle(f"{win.APP_NAME} {win.APP_VERSION}")
    win.resize(1280, 800)
    win.setMinimumSize(960, 640)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
