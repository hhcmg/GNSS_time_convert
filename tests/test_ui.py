"""Headless regressions for editable time fields and toolbar state.

Run with: .venv/Scripts/python.exe -m unittest discover -s tests -p test_ui.py
"""

import datetime
import os
import sys
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from src.qtTimeTool import TimeToolWidget, parse_value


BASE_UTC = datetime.datetime(2024, 1, 1, 12, 34, 56)
LEAP_TRANSITIONS = (
    (1981, 7, 1), (1982, 7, 1), (1983, 7, 1), (1985, 7, 1),
    (1988, 1, 1), (1990, 1, 1), (1991, 1, 1), (1992, 7, 1),
    (1993, 7, 1), (1994, 7, 1), (1996, 1, 1), (1997, 7, 1),
    (1999, 1, 1), (2006, 1, 1), (2009, 1, 1), (2012, 7, 1),
    (2015, 7, 1), (2017, 1, 1),
)


class TimeToolWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        self.widget = TimeToolWidget()
        self.widget._last_utc = BASE_UTC
        self.widget._fill_all(BASE_UTC, source=None)
        self.widget.show()
        self._drain()

    def tearDown(self):
        self.widget._timer.stop()
        self.widget.close()
        self.widget.deleteLater()
        self._drain()

    def _drain(self):
        # A focus change can enqueue a zero-delay commit, which may in turn
        # enqueue selection/layout work. Flush those before the next action.
        for _ in range(3):
            self.app.processEvents()

    def _click(self, button):
        # QTest.mouseClick sends press/release in one tick. Real users give the
        # deferred focus-out commit a chance to run before releasing a button.
        escaped = []
        with patch.object(sys, "excepthook", side_effect=lambda *args: escaped.append(args)):
            QTest.mousePress(button, Qt.LeftButton)
            self._drain()
            QTest.mouseRelease(button, Qt.LeftButton)
            self._drain()
        self.assertEqual([], escaped, "An exception escaped the button slot")

    def _type(self, edit, text):
        edit.setFocus()
        self._drain()
        edit.selectAll()
        if text:
            QTest.keyClicks(edit, text)
        else:
            QTest.keyClick(edit, Qt.Key_Backspace)

    def _enter(self, edit):
        # PyQt routes uncaught slot exceptions to sys.excepthook; its default
        # hook may abort the process. Capture them and fail the test instead.
        escaped = []
        with patch.object(sys, "excepthook", side_effect=lambda *args: escaped.append(args)):
            QTest.keyClick(edit, Qt.Key_Return)
            self._drain()
        self.assertEqual([], escaped, "An exception escaped the Return key slot")

    def _snapshot(self, exclude=None):
        return {
            identity: cell.get_text()
            for identity, cell in self.widget.cells.items()
            if not cell.disabled and identity != exclude
        }

    def _assert_empty(self):
        for identity, cell in self.widget.cells.items():
            if not cell.disabled:
                with self.subTest(cell=identity):
                    self.assertEqual("", cell.get_text())

    def _assert_rejected(self, identity, expected_outputs, expected_utc=BASE_UTC):
        self.assertEqual(expected_utc, self.widget._last_utc)
        self.assertEqual(expected_outputs, self._snapshot(exclude=identity))
        cell = self.widget.cells[identity]
        visible_edits = cell.subs if cell.split_mode else [cell.combined]
        self.assertTrue(any(edit.property("error") for edit in visible_edits))
        self.assertEqual("err", self.widget.status_lb.property("level"))

    def test_missing_split_fields_do_not_shift_later_values(self):
        self._click(self.widget.btn_split)
        cases = (
            ("UTC", "ydoy", ("2026", "", "100")),
            ("UTC", "ydoy", ("", "100", "5")),
            ("UTC", "mjdsod", ("", "60000")),
            ("GPST", "weekdow", ("2400", "", "5")),
        )
        for system, key, parts in cases:
            with self.subTest(system=system, key=key, parts=parts):
                self.widget._last_utc = BASE_UTC
                self.widget._fill_all(BASE_UTC, source=None)
                identity = (system, key)
                expected = self._snapshot(exclude=identity)
                cell = self.widget.cells[identity]
                for edit, value in zip(cell.subs, parts):
                    self._type(edit, value)
                self._enter(cell.subs[-1])
                self._assert_rejected(identity, expected)
                self.assertEqual(list(parts), [edit.text() for edit in cell.subs])

    def test_clear_stays_empty_when_switching_to_split(self):
        self._click(self.widget.btn_clear)
        self._assert_empty()
        self._click(self.widget.btn_split)
        self._assert_empty()
        self._click(self.widget.btn_split)
        self._assert_empty()

    def test_clear_stays_empty_when_switching_to_combined(self):
        self._click(self.widget.btn_split)
        self._click(self.widget.btn_clear)
        self._assert_empty()
        self._click(self.widget.btn_split)
        self._assert_empty()
        self._click(self.widget.btn_split)
        self._assert_empty()

    def test_restoring_committed_value_clears_validation_error(self):
        cell = self.widget.cells[("UTC", "cal")]
        original = cell.get_text()
        self._type(cell.combined, "bad")
        self._enter(cell.combined)
        self.assertTrue(cell.combined.property("error"))
        self._type(cell.combined, original)
        self._enter(cell.combined)
        self.assertFalse(cell.combined.property("error"))
        self.assertNotEqual("err", self.widget.status_lb.property("level"))
        self.assertEqual(BASE_UTC, self.widget._last_utc)

    def test_restoring_split_committed_value_clears_validation_error(self):
        self._click(self.widget.btn_split)
        cell = self.widget.cells[("UTC", "cal")]
        month = cell.subs[1]
        original = month.text()
        self._type(month, "99")
        self._enter(month)
        self.assertTrue(any(edit.property("error") for edit in cell.subs))
        self._type(month, original)
        self._enter(month)
        self.assertFalse(any(edit.property("error") for edit in cell.subs))
        self.assertNotEqual("err", self.widget.status_lb.property("level"))
        self.assertEqual(BASE_UTC, self.widget._last_utc)

    def test_empty_split_calendar_cannot_copy_separator_text(self):
        self._click(self.widget.btn_split)
        self._click(self.widget.btn_clear)
        self.app.clipboard().setText("previous clipboard content")
        self.widget._copy_value("UTC", "cal")
        self.assertEqual("previous clipboard content", self.app.clipboard().text())
        self.assertEqual("", self.widget.cells[("UTC", "cal")].get_text())

    def test_leaving_empty_split_calendar_does_not_show_validation_error(self):
        self._click(self.widget.btn_split)
        self._click(self.widget.btn_clear)
        cell = self.widget.cells[("UTC", "cal")]
        cell.subs[0].setFocus()
        self._drain()
        self.widget.btn_split.setFocus()
        self._drain()
        self.assertFalse(any(edit.property("error") for edit in cell.subs))
        self.assertNotEqual("err", self.widget.status_lb.property("level"))

    def test_extreme_dates_are_rejected_without_partial_state_updates(self):
        identity = ("UTC", "cal")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        for value in ("9999-12-31 23:59:50", "0001-01-01 00:00:00"):
            with self.subTest(value=value):
                self.widget._last_utc = BASE_UTC
                self.widget._fill_all(BASE_UTC, source=None)
                self._type(cell.combined, value)
                self._enter(cell.combined)
                self._assert_rejected(identity, expected)
                self.assertEqual(value, cell.get_text())

    def test_all_18_unrepresentable_leap_seconds_are_rejected(self):
        identity = ("GPST", "cal")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        for offset, parts in enumerate(LEAP_TRANSITIONS, start=1):
            transition = datetime.datetime(*parts)
            gpst_leap_second = transition + datetime.timedelta(seconds=offset - 1)
            value = gpst_leap_second.strftime("%Y-%m-%d %H:%M:%S")
            with self.subTest(transition=transition.date(), gpst=value):
                self.widget._last_utc = BASE_UTC
                self.widget._fill_all(BASE_UTC, source=None)
                self._type(cell.combined, value)
                self._enter(cell.combined)
                self._assert_rejected(identity, expected)
                self.assertEqual(value, cell.get_text())

    def test_valid_conversion_updates_every_enabled_field(self):
        cell = self.widget.cells[("UTC", "cal")]
        value = "2026-01-02 03:04:05.125"
        expected_utc = datetime.datetime(2026, 1, 2, 3, 4, 5, 125000)
        self._type(cell.combined, value)
        self._enter(cell.combined)
        self.assertEqual(expected_utc, self.widget._last_utc)
        expected_times = {
            "UTC": expected_utc,
            "GPST": expected_utc + datetime.timedelta(seconds=18),
            "BDT": expected_utc + datetime.timedelta(seconds=4),
        }
        for (system, key), result in self.widget.cells.items():
            if result.disabled:
                continue
            with self.subTest(system=system, key=key):
                converted = parse_value(system, key, result.get_text())
                # MJD(float) is displayed at finite precision.
                self.assertLessEqual(abs((converted - expected_times[system]).total_seconds()), 0.001)
                self.assertFalse(any(edit.property("error") for edit in result._edits))

    def test_live_updates_and_locks_fields_then_stops(self):
        first = datetime.datetime(2026, 5, 6, 7, 8, 9)
        second = first + datetime.timedelta(seconds=1)
        with patch("src.qtTimeTool.utc_now_naive", return_value=first):
            self._click(self.widget.btn_live)
        self.assertTrue(self.widget._live)
        self.assertTrue(self.widget._timer.isActive())
        self.assertEqual(first, self.widget._last_utc)
        for cell in self.widget.cells.values():
            if not cell.disabled:
                self.assertTrue(all(edit.isReadOnly() for edit in cell._edits))
        with patch("src.qtTimeTool.utc_now_naive", return_value=second):
            self.widget._tick()
        self.assertEqual(second, self.widget._last_utc)
        self._click(self.widget.btn_live)
        self.assertFalse(self.widget._live)
        self.assertFalse(self.widget._timer.isActive())
        for cell in self.widget.cells.values():
            if not cell.disabled:
                self.assertTrue(all(not edit.isReadOnly() for edit in cell._edits))

    def test_now_stops_live_and_sets_current_time(self):
        first = datetime.datetime(2026, 5, 6, 7, 8, 9)
        now = datetime.datetime(2026, 5, 7, 1, 2, 3)
        with patch("src.qtTimeTool.utc_now_naive", return_value=first):
            self._click(self.widget.btn_live)
        with patch("src.qtTimeTool.utc_now_naive", return_value=now):
            self._click(self.widget.btn_now)
        self.assertEqual(now, self.widget._last_utc)
        self.assertFalse(self.widget._live)
        self.assertFalse(self.widget.btn_live.isChecked())
        self.assertFalse(self.widget._timer.isActive())

    def test_split_toggle_preserves_valid_unsubmitted_input(self):
        cell = self.widget.cells[("UTC", "cal")]
        target = datetime.datetime(2026, 2, 3, 4, 5, 6)
        self._type(cell.combined, "2026-02-03 04:05:06")
        self._click(self.widget.btn_split)
        self.assertEqual(target, parse_value("UTC", "cal", cell.get_text()))
        self._click(self.widget.btn_split)
        self.assertEqual(target, parse_value("UTC", "cal", cell.get_text()))

    def test_split_toggle_preserves_invalid_unsubmitted_input(self):
        identity = ("UTC", "cal")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        value = "2026-02-31 04:05:06"
        self._type(cell.combined, value)
        self._click(self.widget.btn_split)
        self.assertEqual(value, cell.get_text())
        self.assertEqual(BASE_UTC, self.widget._last_utc)
        self.assertEqual(expected, self._snapshot(exclude=identity))
        self._click(self.widget.btn_split)
        self.assertEqual(value, cell.get_text())
        self.assertEqual(BASE_UTC, self.widget._last_utc)
        self.assertEqual(expected, self._snapshot(exclude=identity))

    def test_switching_to_combined_preserves_invalid_split_input(self):
        self._click(self.widget.btn_split)
        identity = ("UTC", "cal")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        self._type(cell.subs[1], "99")
        draft = cell.get_text()
        self._click(self.widget.btn_split)
        self.assertEqual(draft, cell.get_text())
        self.assertEqual(BASE_UTC, self.widget._last_utc)
        self.assertEqual(expected, self._snapshot(exclude=identity))
        self._click(self.widget.btn_split)
        self.assertEqual("99", cell.subs[1].text())
        self.assertEqual(draft, cell.get_text())

    def test_malformed_combined_draft_survives_split_round_trip(self):
        identity = ("UTC", "cal")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        for value in ("invalid", "bad input"):
            with self.subTest(value=value):
                self.widget._fill_all(BASE_UTC, source=None)
                self._type(cell.combined, value)
                self._click(self.widget.btn_split)
                self.assertTrue(any(value in edit.text() for edit in cell.subs))
                self.assertEqual(BASE_UTC, self.widget._last_utc)
                self._click(self.widget.btn_split)
                self.assertEqual(value, cell.get_text())
                self.assertEqual(BASE_UTC, self.widget._last_utc)
                self.assertEqual(expected, self._snapshot(exclude=identity))

    def test_incomplete_split_draft_stays_invalid_after_mode_round_trip(self):
        self._click(self.widget.btn_split)
        identity = ("UTC", "ydoy")
        cell = self.widget.cells[identity]
        expected = self._snapshot(exclude=identity)
        parts = ["2026", "", "100"]
        for edit, value in zip(cell.subs, parts):
            self._type(edit, value)
        self._click(self.widget.btn_split)
        self.assertIn("?", cell.get_text())
        self._enter(cell.combined)
        self._assert_rejected(identity, expected)
        self._click(self.widget.btn_split)
        self.assertEqual(parts, [edit.text() for edit in cell.subs])
        self.assertEqual(BASE_UTC, self.widget._last_utc)
        self.assertEqual(expected, self._snapshot(exclude=identity))


if __name__ == "__main__":
    unittest.main()
