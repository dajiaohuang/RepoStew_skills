import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pr_tracker
import state_store


class CheckpointGuardTests(unittest.TestCase):
    def test_legacy_checkpoint_cannot_claim_handled_coverage_after_v2_install(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'REPOSTEW_HOME': temp}):
            home = Path(temp)
            with state_store.connect(home, create=True) as db:
                db.execute('CREATE TABLE event_cursors (source TEXT PRIMARY KEY)')
            with self.assertRaisesRegex(ValueError, 'bare handled checkpoints'):
                pr_tracker.save_notification_checkpoint('github', '2026-01-01T00:00:00+00:00')
            self.assertEqual(state_store.load_document(home, 'notification_checkpoints.json', {}), {})


if __name__ == '__main__':
    unittest.main()
