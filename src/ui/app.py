"""Cross-platform Qt Quick entry point for Mission Control."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from src.ui.controller import MissionControlController


def configure_qt_plugin_paths():
    """Use plugins shipped with this interpreter's PySide6 installation."""

    plugin_root = Path(
        QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    ).resolve()
    platform_root = plugin_root / "platforms"
    if not platform_root.is_dir():
        raise RuntimeError(
            "PySide6 platform plugins are missing from "
            f"{platform_root}. Reinstall PySide6 in the active environment."
        )
    QCoreApplication.setLibraryPaths([str(plugin_root)])
    os.environ["QT_PLUGIN_PATH"] = str(plugin_root)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_root)
    return platform_root


def run(controller=None):
    configure_qt_plugin_paths()
    QQuickStyle.setStyle("Basic")
    application = QGuiApplication(sys.argv)
    application.setApplicationName("Skunkworks")
    application.setOrganizationName("Skunkworks")

    engine = QQmlApplicationEngine()
    qml_root = Path(__file__).parent / "qml"
    engine.addImportPath(str(qml_root))
    engine.load(QUrl.fromLocalFile(str(qml_root / "App.qml")))

    if not engine.rootObjects():
        return 1
    controller = controller or MissionControlController()
    engine.rootObjects()[0].setProperty("backend", controller)
    QTimer.singleShot(0, controller.start)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(run())
