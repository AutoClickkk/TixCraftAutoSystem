from __future__ import annotations
import time
from threading import Event
from unittest.mock import MagicMock

import pytest

from src.services.grabtickets import GrabTickets, StopRequested


@pytest.fixture
def grab():
    g = GrabTickets()
    # reset injectable callbacks between tests
    g.set_stop_event(None)
    g.set_manual_captcha_callback(None)
    g.set_manual_resume_callback(None)
    g.set_status_callback(None)
    return g


def test_sleep_respects_bounds(grab):
    config = {"sleep": {"min_seconds": 0.1, "max_seconds": 0.2}}
    samples = []
    for _ in range(20):
        t0 = time.monotonic()
        grab._sleep(config)
        samples.append(time.monotonic() - t0)
    # Allow timer slop on both ends but ensure we're inside the window.
    assert min(samples) >= 0.08
    assert max(samples) <= 0.35


def test_sleep_handles_inverted_bounds(grab):
    # max < min should be clamped, not crash
    config = {"sleep": {"min_seconds": 0.3, "max_seconds": 0.1}}
    grab._sleep(config)  # should not raise


def test_check_stop_raises_when_event_set(grab):
    ev = Event()
    grab.set_stop_event(ev)
    ev.set()
    with pytest.raises(StopRequested):
        grab._check_stop()


def test_check_stop_silent_when_event_clear(grab):
    grab.set_stop_event(Event())
    grab._check_stop()  # should not raise


def test_status_callback_invoked(grab):
    received = []
    grab.set_status_callback(received.append)
    grab._status("hello")
    assert received == ["hello"]


def test_status_callback_failure_does_not_propagate(grab):
    def boom(_s):
        raise RuntimeError("kaboom")
    grab.set_status_callback(boom)
    # should swallow the exception
    grab._status("hi")


def test_send_notifications_no_emails_does_nothing(grab):
    smtp_mock = MagicMock()
    grab._smtp_utils = smtp_mock
    grab._send_notifications({"notification_emails": []})
    grab._send_notifications({"notification_emails": None})
    smtp_mock.send.assert_not_called()


def test_max_retries_constants_are_positive():
    assert GrabTickets.MAX_OCR_RETRIES > 0
    assert GrabTickets.MAX_CAPTCHA_SUBMIT_RETRIES > 0
    assert GrabTickets.MAX_RESTART_RETRIES > 0
