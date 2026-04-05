import os
import unittest


class TestUiBackup(unittest.TestCase):
    """确保 UI 改造前保留了可回退的原始文件副本。"""

    def test_backup_file_exists_before_visual_refresh(self):
        backup_path = os.path.join(os.path.dirname(__file__), "..", "app_backup_2026_04_06.py")
        self.assertTrue(os.path.exists(os.path.abspath(backup_path)))
