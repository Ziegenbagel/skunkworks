import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QLibraryInfo

from src.application.paths import ApplicationPaths
from src.ui.app import acquire_instance_lock, configure_qt_plugin_paths
import skunkworks_launcher


class QtApplicationBootstrapTests(unittest.TestCase):
    def test_console_launcher_imports_ui_after_restoring_package_root(self):
        expected_root = str(Path(skunkworks_launcher.__file__).resolve().parent)
        with patch.object(sys, "path", [entry for entry in sys.path if entry != expected_root]):
            with patch("src.ui.app.run", return_value=17) as application_run:
                self.assertEqual(skunkworks_launcher.run(), 17)
        application_run.assert_called_once_with()

    def test_only_one_instance_can_hold_a_data_root_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = ApplicationPaths(
                root / "data", root / "config", root / "cache", root / "state",
            )
            first = acquire_instance_lock(paths)
            second = acquire_instance_lock(paths)

            self.assertIsNotNone(first)
            self.assertIsNone(second)
            first.unlock()
            self.assertIsNotNone(acquire_instance_lock(paths))

    def test_frozen_launcher_never_uses_home_qt_installation(self):
        bundled_plugins = Path(
            QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
        ).resolve()
        with patch.object(sys, "frozen", True, create=True):
            platform_root = configure_qt_plugin_paths()

        self.assertEqual(platform_root, bundled_plugins / "platforms")

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
