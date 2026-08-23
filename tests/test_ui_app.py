import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

from src.ui.app import configure_qt_plugin_paths


class QtApplicationBootstrapTests(unittest.TestCase):
    def test_launcher_uses_active_pyside_platform_plugins(self):
        with patch.dict(os.environ, {}, clear=False):
            platform_root = configure_qt_plugin_paths()

            expected_plugin = (
                "libqcocoa.dylib" if sys.platform == "darwin"
                else "qwindows.dll" if sys.platform.startswith("win")
                else "libqxcb.so"
            )
            self.assertTrue((platform_root / expected_plugin).exists())
            self.assertEqual(
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"],
                str(platform_root),
            )
            self.assertEqual(
                QCoreApplication.libraryPaths(),
                [str(platform_root.parent)],
            )


if __name__ == "__main__":
    unittest.main()
