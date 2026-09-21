from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import helpers

from sdlc_lib import checks_lock
from sdlc_lib.result import Result


def clock_at(dt: datetime):
    return lambda: dt


BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class LockTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def lock_file(self):
        return self.repo.root / ".sdlc" / "lock"

    def read_lease(self):
        return json.loads(self.lock_file().read_text())


class AcquireTests(LockTestCase):
    def test_acquire_creates_lock_dir_and_file(self):
        result = Result()
        checks_lock.acquire(self.repo.root, "session-a", result, clock=clock_at(BASE_TIME))
        self.assertTrue(result.ok, result.to_dict())
        self.assertTrue(self.lock_file().is_file())
        data = self.read_lease()
        self.assertEqual(data["session"], "session-a")
        self.assertEqual(data["started"], "2026-01-01T12:00:00Z")
        self.assertEqual(data["refreshed"], "2026-01-01T12:00:00Z")

    def test_acquire_by_same_session_refreshes_and_keeps_started(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        later = BASE_TIME + timedelta(minutes=30)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "session-a", r2, clock=clock_at(later))
        self.assertTrue(r2.ok, r2.to_dict())
        self.assertEqual(r2.extra["action"], "refreshed")
        data = self.read_lease()
        self.assertEqual(data["started"], "2026-01-01T12:00:00Z")
        self.assertEqual(data["refreshed"], "2026-01-01T12:30:00Z")

    def test_acquire_by_other_session_fails_while_held(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        later = BASE_TIME + timedelta(minutes=5)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "session-b", r2, clock=clock_at(later))
        self.assertFalse(r2.ok)
        self.assertEqual(r2.exit_code(), 1)
        self.assertEqual([d.code for d in r2.errors], ["lock-held"])
        data = self.read_lease()
        self.assertEqual(data["session"], "session-a")

    def test_empty_token_never_matches_even_itself(self):
        checks_lock.acquire(self.repo.root, "", Result(), clock=clock_at(BASE_TIME))
        later = BASE_TIME + timedelta(minutes=5)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "", r2, clock=clock_at(later))
        self.assertFalse(r2.ok)
        self.assertEqual([d.code for d in r2.errors], ["lock-held"])

    def test_force_takes_over_a_held_lease(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        later = BASE_TIME + timedelta(minutes=5)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "session-b", r2, force=True, clock=clock_at(later))
        self.assertTrue(r2.ok, r2.to_dict())
        self.assertEqual(r2.extra["action"], "taken-over")
        data = self.read_lease()
        self.assertEqual(data["session"], "session-b")

    def test_expired_lease_can_be_acquired_without_force(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        expired = BASE_TIME + timedelta(hours=2, minutes=1)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "session-b", r2, clock=clock_at(expired))
        self.assertTrue(r2.ok, r2.to_dict())
        data = self.read_lease()
        self.assertEqual(data["session"], "session-b")
        self.assertEqual(data["started"], "2026-01-01T14:01:00Z")

    def test_lease_held_just_under_two_hours(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        almost_expired = BASE_TIME + timedelta(hours=1, minutes=59)
        r2 = Result()
        checks_lock.acquire(self.repo.root, "session-b", r2, clock=clock_at(almost_expired))
        self.assertFalse(r2.ok)

    def test_invalid_lock_file_is_fatal(self):
        (self.repo.root / ".sdlc").mkdir(parents=True, exist_ok=True)
        self.lock_file().write_text("not json")
        r = Result()
        checks_lock.acquire(self.repo.root, "session-a", r, clock=clock_at(BASE_TIME))
        self.assertEqual(r.exit_code(), 2)
        self.assertEqual([d.code for d in r.errors], ["lock-invalid"])


class ReleaseTests(LockTestCase):
    def test_release_by_holder_removes_lock(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        r = Result()
        checks_lock.release(self.repo.root, "session-a", r, clock=clock_at(BASE_TIME))
        self.assertTrue(r.ok, r.to_dict())
        self.assertFalse(self.lock_file().exists())

    def test_release_by_other_session_fails_without_force(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        r = Result()
        later = BASE_TIME + timedelta(minutes=5)
        checks_lock.release(self.repo.root, "session-b", r, clock=clock_at(later))
        self.assertFalse(r.ok)
        self.assertEqual([d.code for d in r.errors], ["lock-held"])
        self.assertTrue(self.lock_file().exists())

    def test_release_by_other_session_with_force_succeeds(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        r = Result()
        later = BASE_TIME + timedelta(minutes=5)
        checks_lock.release(self.repo.root, "session-b", r, force=True, clock=clock_at(later))
        self.assertTrue(r.ok, r.to_dict())
        self.assertFalse(self.lock_file().exists())

    def test_release_with_no_lock_is_a_no_op(self):
        r = Result()
        checks_lock.release(self.repo.root, "session-a", r, clock=clock_at(BASE_TIME))
        self.assertTrue(r.ok)
        self.assertEqual(r.extra["action"], "not-held")

    def test_release_of_expired_lease_by_anyone_succeeds(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        expired = BASE_TIME + timedelta(hours=3)
        r = Result()
        checks_lock.release(self.repo.root, "session-b", r, clock=clock_at(expired))
        self.assertTrue(r.ok, r.to_dict())
        self.assertFalse(self.lock_file().exists())


class StatusTests(LockTestCase):
    def test_status_unlocked(self):
        r = Result()
        checks_lock.status(self.repo.root, r, clock=clock_at(BASE_TIME))
        self.assertTrue(r.ok)
        self.assertEqual(r.exit_code(), 0)
        self.assertFalse(r.extra["locked"])
        self.assertFalse(r.extra["held"])

    def test_status_held(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        r = Result()
        checks_lock.status(self.repo.root, r, clock=clock_at(BASE_TIME + timedelta(minutes=1)))
        self.assertTrue(r.ok)
        self.assertTrue(r.extra["locked"])
        self.assertTrue(r.extra["held"])
        self.assertEqual(r.extra["session"], "session-a")

    def test_status_expired_reports_not_held(self):
        checks_lock.acquire(self.repo.root, "session-a", Result(), clock=clock_at(BASE_TIME))
        r = Result()
        expired = BASE_TIME + timedelta(hours=3)
        checks_lock.status(self.repo.root, r, clock=clock_at(expired))
        self.assertTrue(r.ok)
        self.assertTrue(r.extra["locked"])
        self.assertFalse(r.extra["held"])

    def test_status_always_exits_0_even_for_invalid_lock_file(self):
        (self.repo.root / ".sdlc").mkdir(parents=True, exist_ok=True)
        self.lock_file().write_text("not json")
        r = Result()
        checks_lock.status(self.repo.root, r, clock=clock_at(BASE_TIME))
        self.assertEqual(r.exit_code(), 0)
        self.assertFalse(r.fatal)
        self.assertTrue(r.extra["locked"])
        self.assertFalse(r.extra["held"])
        self.assertEqual([w.code for w in r.warnings], ["lock-invalid"])


if __name__ == "__main__":
    unittest.main()
