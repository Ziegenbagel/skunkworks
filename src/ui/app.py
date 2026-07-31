"""Cross-platform Qt Quick entry point for Mission Control."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def run():
    application = QGuiApplication(sys.argv)
    application.setApplicationName("Skunkworks")
    application.setOrganizationName("Skunkworks")

    engine = QQmlApplicationEngine()
    qml_root = Path(__file__).parent / "qml"
    engine.addImportPath(str(qml_root))
    engine.load(QUrl.fromLocalFile(str(qml_root / "App.qml")))

    if not engine.rootObjects():
        return 1
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(run())
