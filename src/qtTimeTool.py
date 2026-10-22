# -*- coding: utf-8 -*-
"""A compact three-system time workbench built with native Qt widgets."""

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QFontDatabase, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QSizePolicy, QStackedWidget, QScrollArea,
)

# Keep the original module's conversion API available for existing callers.
from .time_conversion import *
from .ui_styles import STYLESHEET


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _measure_text(font, sample):
    metrics = QFontMetrics(font)
    return metrics.horizontalAdvance(sample) + 22


class CurrentPageStack(QStackedWidget):
    """Hidden split fields must not determine the combined layout's height."""
    def sizeHint(self):
        current = self.currentWidget()
        return current.sizeHint() if current else QSize(0, 0)

    def minimumSizeHint(self):
        current = self.currentWidget()
        return current.minimumSizeHint() if current else QSize(0, 0)


class ValueEdit(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)


class FieldCell:
    def __init__(self, system, key, mono, on_commit, disabled=False):
        self.system, self.key = system, key
        self.disabled = disabled
        self.on_commit = on_commit
        self.split_mode = False
        self._synced_combined = ""
        self._split_entry_parts = ()
        self._combined_entry = ""
        self.stack = CurrentPageStack()
        self.stack.setObjectName("cellStack")
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combined_wrap = QFrame()
        combined_wrap.setObjectName("comboWrap")
        combined_layout = QVBoxLayout(combined_wrap)
        combined_layout.setContentsMargins(0, 0, 0, 0)
        self.combined = ValueEdit()
        self.combined.setObjectName("val")
        self.combined.setFont(mono)
        self.combined.setMinimumWidth(_measure_text(mono, "2026-10-22 00:00:00.000"))
        self.combined.setAccessibleName(f"{system} {LABELS[key]}")
        self.combined.setPlaceholderText(HINTS[key])
        self.combined.setToolTip(f"{HINTS[key]}\nPress Enter to convert all systems.")
        if disabled:
            self.combined.setText("Not applicable")
            self.combined.setEnabled(False)
        combined_layout.addWidget(self.combined)
        self.stack.addWidget(combined_wrap)

        self.split_page = QFrame()
        self.split_page.setObjectName("splitPage")
        split_layout = QVBoxLayout(self.split_page)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(7)
        self.subs, self._sub_meta = [], []
        if not disabled:
            for form_row in SPLIT_FORM[key]:
                row = QGridLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setHorizontalSpacing(7)
                row.setVerticalSpacing(3)
                for column, (caption, sample, stretch) in enumerate(form_row):
                    label = QLabel(caption)
                    label.setObjectName("subLabel")
                    edit = ValueEdit()
                    edit.setObjectName("valSub")
                    edit.setFont(mono)
                    edit.setAlignment(Qt.AlignCenter)
                    edit.setMinimumWidth(_measure_text(mono, sample))
                    edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    edit.setAccessibleName(f"{system} {LABELS[key]} {caption}")
                    edit.setToolTip(f"{caption} — press Enter to convert")
                    row.addWidget(label, 0, column)
                    row.addWidget(edit, 1, column)
                    row.setColumnStretch(column, stretch)
                    self.subs.append(edit)
                    self._sub_meta.append((edit, sample))
                split_layout.addLayout(row)
        self.stack.addWidget(self.split_page)
        self._edits = [self.combined] + self.subs
        for edit in self._edits:
            edit.setProperty("active", False)
            edit.setProperty("error", False)
            if not disabled:
                edit.returnPressed.connect(self._commit_now)
                edit.editingFinished.connect(self._maybe_commit)

    def widget(self):
        return self.stack

    def set_mode(self, split):
        if self.disabled or self.split_mode == split:
            return
        # Keep both representations, including incomplete split drafts. Only
        # re-split when the user actually changed the combined representation.
        if split:
            raw = self.combined.text()
            if raw != self._synced_combined:
                try:
                    normalized = format_value(self.system, self.key,
                                              parse_value(self.system, self.key, raw))
                except (ValueError, OverflowError):
                    normalized = raw
                self._set_subs(split_parts(self.key, normalized))
                self._synced_combined = raw
            self._split_entry_parts = tuple(edit.text() for edit in self.subs)
            self._combined_entry = raw
        else:
            parts = [edit.text() for edit in self.subs]
            if tuple(parts) == self._split_entry_parts:
                raw = self._combined_entry
            else:
                try:
                    raw = join_parts(self.key, parts)
                except ValueError:
                    # Placeholders prevent missing fields from being reinterpreted.
                    visible = [part.strip() or "?" for part in parts]
                    raw = ("-".join(visible[:3]) + " " + ":".join(visible[3:])
                           if self.key == "cal" else " ".join(visible))
            self._set_edit(self.combined, raw)
            self._synced_combined = raw
        self.split_mode = split
        self.stack.setCurrentIndex(1 if split else 0)
        self.stack.updateGeometry()

    @staticmethod
    def _set_edit(edit, text):
        previous = edit.blockSignals(True)
        edit.setText(text)
        edit.setCursorPosition(0)
        edit.blockSignals(previous)

    def _set_subs(self, parts):
        for edit, part in zip(self.subs, parts):
            self._set_edit(edit, part)

    def set_font(self, font):
        for edit in self._edits:
            edit.setFont(font)
        for edit, sample in self._sub_meta:
            edit.setMinimumWidth(_measure_text(font, sample))

    def set_readonly(self, readonly):
        if not self.disabled:
            for edit in self._edits:
                edit.setReadOnly(readonly)

    def _set_property(self, name, value):
        for edit in self._edits:
            if edit.property(name) != value:
                edit.setProperty(name, value)
                _repolish(edit)

    def set_active(self, active):
        self._set_property("active", active)

    def set_error(self, error):
        self._set_property("error", error)

    def clear_error(self):
        self.set_error(False)

    def get_text(self):
        if self.disabled:
            return "—"
        if self.split_mode:
            return join_parts(self.key, [edit.text() for edit in self.subs])
        return self.combined.text()

    def set_text(self, value):
        self._set_edit(self.combined, value)
        self._set_subs(split_parts(self.key, value))
        self._synced_combined = value
        self._split_entry_parts = tuple(edit.text() for edit in self.subs)
        self._combined_entry = value

    def clear(self):
        self.set_text("")

    def _commit_now(self):
        self.on_commit(self.system, self.key)

    def _maybe_commit(self):
        mode = self.split_mode
        QTimer.singleShot(0, lambda: self._commit_if_focus_left(mode))

    def _commit_if_focus_left(self, original_mode=None):
        if original_mode is not None and original_mode != self.split_mode:
            return
        if QApplication.focusWidget() not in self._edits:
            self.on_commit(self.system, self.key)


class TimeToolWidget(QWidget):
    APP_NAME = "GNSS Time Converter"
    APP_VERSION = "V2.2.0"
    AUTHOR_NAME = "Kurt"
    SYSTEMS = ["GPST", "BDT", "UTC"]
    SUBTITLES = {"UTC": "Coordinated Universal Time", "GPST": "GPS Time", "BDT": "BeiDou Time"}
    ROW_HINTS = {"cal": "Date & time", "ydoy": "Year · day of year · seconds",
                 "mjdsod": "Modified Julian day · seconds", "mjdf": "Modified Julian day",
                 "weeksow": "Week · seconds of week", "weekdow": "Week · day · seconds"}

    def __init__(self, chinese=False, parent=None):
        super().__init__(parent)
        self.chinese = chinese
        self.setObjectName("root")
        self.cells, self._committed, self._offset_labels = {}, {}, {}
        self._updating = self._live = self._split = False
        self._last_utc = None
        self._mono = self._pick_mono_font()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._build_ui()
        self._apply_style()
        self._fill_all(utc_now_naive())
        self._set_status("Ready. Edit any value and press Enter.")

    def _pick_mono_font(self):
        available = set(QFontDatabase().families())
        for family in ("Consolas", "DejaVu Sans Mono", "Menlo", "Liberation Mono", "Courier New"):
            if family in available:
                return QFont(family, 10)
        font = QFont("monospace", 10)
        font.setStyleHint(QFont.Monospace)
        return font

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 18)
        root.setSpacing(19)
        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(5)
        for text, name in (("GNSS UTILITIES", "eyebrow"), (self.APP_NAME, "appTitle"),
                           ("Convert one instant across GPS, BeiDou and UTC time.", "appSubtitle")):
            label = QLabel(text)
            label.setObjectName(name)
            title_column.addWidget(label)
        header.addLayout(title_column)
        header.addStretch()
        version = QLabel(self.APP_VERSION)
        version.setObjectName("appVer")
        header.addWidget(version, 0, Qt.AlignTop)
        root.addLayout(header)
        root.addWidget(self._build_top_bar())

        self.scroll = QScrollArea()
        self.scroll.setObjectName("tableScroll")
        self.scroll.viewport().setObjectName("scrollViewport")
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignTop)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table = self._build_table()
        self.scroll.setWidget(self.table)
        root.addWidget(self.scroll, 1)
        root.addWidget(self._build_status_bar())

    def _build_top_bar(self):
        frame = QFrame()
        frame.setObjectName("toolbar")
        bar = QHBoxLayout(frame)
        bar.setContentsMargins(13, 11, 13, 11)
        bar.setSpacing(9)
        self.btn_now = QPushButton("Now")
        self.btn_now.setObjectName("now")
        self.btn_now.setToolTip("Use the current UTC time")
        self.btn_live = QPushButton("Live")
        self.btn_live.setObjectName("live")
        self.btn_live.setCheckable(True)
        self.btn_live.setToolTip("Update every second; pause to edit")
        self.btn_split = QPushButton("Split fields")
        self.btn_split.setCheckable(True)
        self.btn_split.setToolTip("Edit year, day and seconds in separate fields")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("clear")
        for button in (self.btn_now, self.btn_live):
            bar.addWidget(button)
        divider = QFrame()
        divider.setObjectName("toolbarDivider")
        divider.setFixedSize(1, 22)
        bar.addWidget(divider)
        bar.addWidget(self.btn_split)
        bar.addWidget(self.btn_clear)
        bar.addStretch()
        self.toolbar_hint = QLabel("EDIT A VALUE  →  PRESS ENTER")
        self.toolbar_hint.setObjectName("toolbarHint")
        bar.addWidget(self.toolbar_hint)
        for button in (self.btn_now, self.btn_live, self.btn_split, self.btn_clear):
            button.setCursor(Qt.PointingHandCursor)
        self.btn_now.clicked.connect(self._set_now)
        self.btn_live.toggled.connect(self._toggle_live)
        self.btn_split.toggled.connect(self._toggle_split)
        self.btn_clear.clicked.connect(self._clear_all)
        return frame

    def _build_table(self):
        frame = QFrame()
        frame.setObjectName("conversionTable")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        grid = QGridLayout(frame)
        grid.setContentsMargins(21, 14, 21, 12)
        grid.setHorizontalSpacing(19)
        grid.setVerticalSpacing(0)
        label = QLabel("TIME FORMAT")
        label.setObjectName("formatHeader")
        grid.addWidget(label, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        for column, system in enumerate(self.SYSTEMS, 1):
            grid.addWidget(self._build_column_header(system), 0, column)
            grid.setColumnStretch(column, 1)
        grid.setColumnMinimumWidth(0, 158)
        for index, (key, label, _) in enumerate(FORMATS):
            separator = QFrame()
            separator.setObjectName("rowDivider")
            grid.addWidget(separator, index * 2 + 1, 0, 1, 4)
            row_label = QFrame()
            row_label.setObjectName("rowLabel")
            label_layout = QVBoxLayout(row_label)
            label_layout.setContentsMargins(0, 16, 0, 16)
            label_layout.setSpacing(5)
            title = QLabel(label)
            title.setObjectName("rowTitle")
            hint = QLabel(self.ROW_HINTS[key])
            hint.setObjectName("rowHint")
            label_layout.addStretch()
            label_layout.addWidget(title)
            label_layout.addWidget(hint)
            label_layout.addStretch()
            row = index * 2 + 2
            grid.addWidget(row_label, row, 0)
            for column, system in enumerate(self.SYSTEMS, 1):
                cell = FieldCell(system, key, self._mono, self._commit,
                                 disabled=system == "UTC" and key in WEEK_KEYS)
                self.cells[(system, key)] = cell
                wrap = QFrame()
                wrap.setObjectName("valueWrap")
                layout = QVBoxLayout(wrap)
                layout.setContentsMargins(0, 13, 0, 13)
                layout.addWidget(cell.widget())
                grid.addWidget(wrap, row, column)
        note = QLabel("SOD = seconds of day   ·   SOW = seconds of week   ·   DOW = 0–6 (Sunday–Saturday)")
        note.setObjectName("tableNote")
        note.setContentsMargins(0, 7, 0, 0)
        grid.addWidget(note, 13, 0, 1, 4)
        grid.setRowStretch(14, 1)
        return frame

    def _build_column_header(self, system):
        header = QFrame()
        header.setObjectName("columnHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 6, 0, 16)
        layout.setSpacing(6)
        top = QHBoxLayout()
        name = QLabel(system)
        name.setObjectName("systemName")
        top.addWidget(name)
        top.addStretch()
        copy_button = QPushButton("Copy")
        copy_button.setObjectName("headCopy")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setAccessibleName(f"Copy {system} calendar")
        copy_button.setToolTip("Copy the calendar date and time")
        copy_button.clicked.connect(lambda checked=False, current=system: self._copy_value(current, "cal"))
        top.addWidget(copy_button)
        layout.addLayout(top)
        subtitle = QLabel(self.SUBTITLES[system])
        subtitle.setObjectName("systemSub")
        layout.addWidget(subtitle)
        offset = QLabel("Reference" if system == "UTC" else "")
        offset.setObjectName("offset")
        layout.addWidget(offset, 0, Qt.AlignLeft)
        self._offset_labels[system] = offset
        return header

    def _build_status_bar(self):
        frame = QFrame()
        frame.setObjectName("statusBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(1, 0, 1, 0)
        layout.setSpacing(18)
        self.status_lb = QLabel()
        self.status_lb.setObjectName("statusMsg")
        self.status_lb.setWordWrap(True)
        self.status_lb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.status_lb, 1)
        author = QLabel(self.AUTHOR_NAME)
        author.setObjectName("footerAuthor")
        layout.addWidget(author, 0, Qt.AlignRight | Qt.AlignVCenter)
        return frame

    def _commit(self, system, key):
        if self._updating or self._live:
            return
        cell = self.cells[(system, key)]
        try:
            text = cell.get_text()
            if text == self._committed.get((system, key)):
                had_error = any(edit.property("error") for edit in cell._edits)
                cell.clear_error()
                if had_error:
                    self._set_status("Ready. Edit any value and press Enter.")
                return
            utc_dt = to_utc(system, parse_value(system, key, text))
            # Prepare every system and display value before replacing any state.
            self._fill_all(utc_dt, source=(system, key))
        except (ValueError, OverflowError) as error:
            cell.set_error(True)
            message = str(error)
            if isinstance(error, OverflowError):
                message = "Date is outside the range shared by UTC, GPST and BDT."
            self._set_status(f"{system} · {LABELS[key]}: {message}", level="err")
            return
        self._set_status(f"Converted from {system} · {LABELS[key]}.", level="ok")

    def _fill_all(self, utc_dt, source=None):
        dts = {system: from_utc(system, utc_dt) for system in self.SYSTEMS}
        values = {(system, key): format_value(system, key, dts[system])
                  for system in self.SYSTEMS for key, _, _ in FORMATS
                  if not (system == "UTC" and key in WEEK_KEYS)}
        self._updating = True
        try:
            for identity, value in values.items():
                cell = self.cells[identity]
                cell.set_text(value)
                cell.clear_error()
                cell.set_active(identity == source)
            self._committed.update(values)
            self._last_utc = utc_dt
            for system in self.SYSTEMS:
                seconds = int((dts[system] - utc_dt).total_seconds())
                text = "UTC reference" if system == "UTC" else f"UTC {seconds:+d} s"
                self._offset_labels[system].setText(text)
        finally:
            self._updating = False

    def _set_now(self):
        if self._live:
            self.btn_live.setChecked(False)
        self._fill_all(utc_now_naive())
        self._set_status("Set to current time.", level="ok")

    def _toggle_split(self, on):
        self._updating = True
        try:
            for cell in self.cells.values():
                cell.set_mode(on)
            self._split = on
        finally:
            self._updating = False
        self.table.adjustSize()
        self.table.updateGeometry()
        self._set_status("Separate fields. Press Enter to convert." if on
                         else "Combined fields. Press Enter to convert.")

    def _toggle_live(self, on):
        self._live = on
        self.btn_live.setText("Live · running" if on else "Live")
        self.toolbar_hint.setText("LIVE CLOCK  ·  UPDATES EVERY SECOND" if on
                                  else "EDIT A VALUE  →  PRESS ENTER")
        for cell in self.cells.values():
            cell.set_readonly(on)
        if on:
            self._tick()
            self._timer.start()
            self._set_status("Live clock running. Pause Live to edit.")
        else:
            self._timer.stop()
            self._set_status("Live clock paused. Fields are editable.")

    def _tick(self):
        self._fill_all(utc_now_naive())

    def _clear_all(self):
        if self._live:
            self.btn_live.setChecked(False)
        self._updating = True
        try:
            for identity, cell in self.cells.items():
                if cell.disabled:
                    continue
                cell.clear()
                cell.set_active(False)
                cell.clear_error()
                self._committed[identity] = ""
            self._last_utc = None
            for label in self._offset_labels.values():
                label.setText("—")
        finally:
            self._updating = False
        self._set_status("Cleared. Enter a value in any field to convert.")

    def _copy_value(self, system, key):
        try:
            text = self.cells[(system, key)].get_text()
        except ValueError as error:
            self._set_status(f"Cannot copy: {error}", level="err")
            return
        if not text or text == "—":
            self._set_status("Nothing to copy.", level="err")
            return
        QApplication.clipboard().setText(text)
        self._set_status(f"Copied {system} calendar to clipboard.", level="ok")

    def _set_status(self, message, level="info"):
        self.status_lb.setText(message)
        self.status_lb.setProperty("level", level)
        _repolish(self.status_lb)

    def _apply_style(self):
        self.setStyleSheet(STYLESHEET)
