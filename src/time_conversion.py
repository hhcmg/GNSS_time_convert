"""GNSS time conversions and editable display formats, independent of Qt.

Python's datetime cannot represent UTC leap seconds. GNSS instants inside a
leap second are rejected explicitly instead of being mapped to another instant.
"""

import calendar
import datetime
import math
import re


GPS_EPOCH = datetime.datetime(1980, 1, 6)
BDS_EPOCH = datetime.datetime(2006, 1, 1)
MJD_EPOCH = datetime.datetime(1858, 11, 17)

GPS_UTC_OFFSETS = [
    (datetime.datetime(1981, 7, 1), 1), (datetime.datetime(1982, 7, 1), 2),
    (datetime.datetime(1983, 7, 1), 3), (datetime.datetime(1985, 7, 1), 4),
    (datetime.datetime(1988, 1, 1), 5), (datetime.datetime(1990, 1, 1), 6),
    (datetime.datetime(1991, 1, 1), 7), (datetime.datetime(1992, 7, 1), 8),
    (datetime.datetime(1993, 7, 1), 9), (datetime.datetime(1994, 7, 1), 10),
    (datetime.datetime(1996, 1, 1), 11), (datetime.datetime(1997, 7, 1), 12),
    (datetime.datetime(1999, 1, 1), 13), (datetime.datetime(2006, 1, 1), 14),
    (datetime.datetime(2009, 1, 1), 15), (datetime.datetime(2012, 7, 1), 16),
    (datetime.datetime(2015, 7, 1), 17), (datetime.datetime(2017, 1, 1), 18),
]


def _add_delta(dt, **kwargs):
    try:
        return dt + datetime.timedelta(**kwargs)
    except OverflowError as err:
        raise ValueError("Time is outside the supported range (years 1–9999).") from err


def _require_integer(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer.")
    return value


def _integer_text(text, label):
    if re.fullmatch(r"[+-]?[0-9]+", text) is None:
        raise ValueError(f"{label} must be an integer.")
    return int(text)


def _finite_number(value, label):
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite.")
    return value


def _seconds_in_range(value, label, upper):
    _finite_number(value, label)
    if value < 0 or value >= upper:
        raise ValueError(f"{label} is out of range [0, {upper}).")
    return value


def _validate_system(system):
    if system not in ("UTC", "GPST", "BDT"):
        raise ValueError("Unsupported time system.")


def utc_now_naive():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def gps_utc_offset_seconds(utc_dt):
    offset = 0
    for t0, sec in GPS_UTC_OFFSETS:
        if utc_dt < t0:
            break
        offset = sec
    return offset


def utc_to_gpst(utc_dt):
    return _add_delta(utc_dt, seconds=gps_utc_offset_seconds(utc_dt))


def gpst_to_utc(gpst_dt):
    offset = 0
    for boundary, new_offset in GPS_UTC_OFFSETS:
        leap_start = boundary + datetime.timedelta(seconds=offset)
        leap_end = boundary + datetime.timedelta(seconds=new_offset)
        if gpst_dt < leap_start:
            break
        if gpst_dt < leap_end:
            raise ValueError("This instant is in a UTC leap second, which is not supported.")
        offset = new_offset
    return _add_delta(gpst_dt, seconds=-offset)


def utc_to_bdt(utc_dt):
    return _add_delta(utc_dt, seconds=gps_utc_offset_seconds(utc_dt) - 14)


def bdt_to_utc(bdt_dt):
    return gpst_to_utc(_add_delta(bdt_dt, seconds=14))


def to_utc(system, dt_system):
    _validate_system(system)
    if system == "UTC":
        return dt_system
    if system == "GPST":
        return gpst_to_utc(dt_system)
    return bdt_to_utc(dt_system)


def from_utc(system, utc_dt):
    _validate_system(system)
    if system == "UTC":
        return utc_dt
    if system == "GPST":
        return utc_to_gpst(utc_dt)
    return utc_to_bdt(utc_dt)


def _sod(dt):
    return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6


def datetime_to_ydoy_sod(dt):
    day0 = datetime.datetime(dt.year, 1, 1)
    return dt.year, (dt - day0).days + 1, _sod(dt)


def datetime_to_mjd_sod(dt):
    return (dt - MJD_EPOCH).days, _sod(dt)


def datetime_to_mjd_float(dt):
    mjd, sod = datetime_to_mjd_sod(dt)
    return mjd + sod / 86400.0


def datetime_to_week_sow(dt, epoch):
    delta = dt - epoch
    week, dow = divmod(delta.days, 7)
    return week, dow * 86400 + delta.seconds + delta.microseconds / 1e6


def datetime_to_week_dow(dt, epoch):
    return divmod((dt - epoch).days, 7)


def ymd_hms_to_datetime(date_text, time_text):
    ymd = date_text.strip().replace("/", "-")
    hms = time_text.strip() or "00:00:00"
    if not ymd:
        raise ValueError("Date is required.")
    combo = ymd + " " + hms
    pattern = "%Y-%m-%d %H:%M:%S.%f" if "." in hms else "%Y-%m-%d %H:%M:%S"
    return datetime.datetime.strptime(combo, pattern)


def ydoy_sod_to_datetime(year, doy, sod):
    _require_integer(year, "Year")
    _require_integer(doy, "DOY")
    day0 = datetime.datetime(year, 1, 1)
    last_doy = 366 if calendar.isleap(year) else 365
    if doy < 1 or doy > last_doy:
        raise ValueError(f"DOY is out of range [1, {last_doy}] for {year}.")
    _seconds_in_range(sod, "SOD", 86400)
    return _add_delta(day0, days=doy - 1, seconds=sod)


def mjd_sod_to_datetime(mjd, sod):
    _require_integer(mjd, "MJD")
    _seconds_in_range(sod, "SOD", 86400)
    return _add_delta(MJD_EPOCH, days=mjd, seconds=sod)


def mjd_float_to_datetime(mjd_float):
    _finite_number(mjd_float, "MJD")
    mjd = math.floor(mjd_float)
    return mjd_sod_to_datetime(mjd, (mjd_float - mjd) * 86400.0)


def week_sow_to_datetime(week, sow, epoch):
    _require_integer(week, "Week")
    _seconds_in_range(sow, "SOW", 604800)
    return _add_delta(epoch, weeks=week, seconds=sow)


def week_dow_sod_to_datetime(week, dow, sod, epoch):
    _require_integer(week, "Week")
    _require_integer(dow, "DOW")
    if dow < 0 or dow > 6:
        raise ValueError("DOW is out of range [0, 6].")
    _seconds_in_range(sod, "SOD", 86400)
    return _add_delta(epoch, weeks=week, days=dow, seconds=sod)


FORMATS = [
    ("cal", "Calendar", "YYYY-MM-DD HH:MM:SS"),
    ("ydoy", "Year DOY SOD", "YYYY DOY SOD"),
    ("mjdsod", "MJD SOD", "MJD SOD"),
    ("mjdf", "MJD (float)", "MJD.frac"),
    ("weeksow", "Week SOW", "WEEK SOW"),
    ("weekdow", "Week DOW SOD", "WEEK DOW SOD"),
]
LABELS = {key: label for key, label, _ in FORMATS}
HINTS = {key: hint for key, _, hint in FORMATS}
WEEK_KEYS = {"weeksow", "weekdow"}

# Flattened field order is shared by the UI, join_parts, and split_parts.
SPLIT_FORM = {
    "cal": [
        [("Year", "2026", 1), ("Month", "00", 1), ("Day", "00", 1)],
        [("Hour", "00", 1), ("Min", "00", 1), ("Sec", "00.000", 1)],
    ],
    "ydoy": [[("Year", "2026", 1), ("DOY", "000", 1), ("SOD", "00000.000", 2)]],
    "mjdsod": [[("MJD", "00000", 1), ("SOD", "00000.000", 2)]],
    "mjdf": [[("MJD", "00000.000000000", 1)]],
    "weeksow": [[("Week", "0000", 1), ("SOW", "000000.000", 2)]],
    "weekdow": [[("Week", "0000", 1), ("DOW", "0", 1), ("SOD", "00000.000", 2)]],
}


def format_value(system, key, dt):
    _validate_system(system)
    # Truncate the complete timestamp once, so every representation agrees and
    # formatting a fractional second never creates SOD=86400 or SOW=604800.
    dt = dt.replace(microsecond=dt.microsecond // 1000 * 1000)
    if key == "cal":
        return (f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} "
                f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond // 1000:03d}")
    if key == "ydoy":
        y, doy, sod = datetime_to_ydoy_sod(dt)
        return f"{y} {doy:03d} {sod:.3f}"
    if key == "mjdsod":
        mjd, sod = datetime_to_mjd_sod(dt)
        return f"{mjd} {sod:.3f}"
    if key == "mjdf":
        return f"{datetime_to_mjd_float(dt):.9f}"
    if key in WEEK_KEYS:
        if system == "UTC":
            return "—"
        epoch = GPS_EPOCH if system == "GPST" else BDS_EPOCH
        if key == "weeksow":
            week, sow = datetime_to_week_sow(dt, epoch)
            return f"{week} {sow:.3f}"
        week, dow = datetime_to_week_dow(dt, epoch)
        return f"{week} {dow} {_sod(dt):.3f}"
    raise ValueError("Unsupported format.")


def _field_count(parts, minimum, maximum, expected):
    if not minimum <= len(parts) <= maximum:
        raise ValueError(f"Expected: {expected}")


def parse_value(system, key, text):
    _validate_system(system)
    t = text.strip()
    if not t or t in ("-", "—"):
        raise ValueError("Empty input.")
    if system == "UTC" and key in WEEK_KEYS:
        raise ValueError("UTC has no GNSS week format.")
    parts = t.split()
    try:
        if key == "cal":
            _field_count(parts, 1, 2, "YYYY-MM-DD [HH:MM:SS]")
            return ymd_hms_to_datetime(parts[0], parts[1] if len(parts) == 2 else "")
        if key == "ydoy":
            _field_count(parts, 2, 3, "Year DOY [SOD]")
            sod = float(parts[2]) if len(parts) == 3 else 0.0
            return ydoy_sod_to_datetime(_integer_text(parts[0], "Year"),
                                        _integer_text(parts[1], "DOY"), sod)
        if key == "mjdsod":
            _field_count(parts, 1, 2, "MJD [SOD]")
            sod = float(parts[1]) if len(parts) == 2 else 0.0
            return mjd_sod_to_datetime(_integer_text(parts[0], "MJD"), sod)
        if key == "mjdf":
            _field_count(parts, 1, 1, "MJD.frac")
            return mjd_float_to_datetime(float(parts[0]))
        epoch = GPS_EPOCH if system == "GPST" else BDS_EPOCH
        if key == "weeksow":
            _field_count(parts, 2, 2, "Week SOW")
            return week_sow_to_datetime(_integer_text(parts[0], "Week"), float(parts[1]), epoch)
        if key == "weekdow":
            _field_count(parts, 2, 3, "Week DOW [SOD]")
            sod = float(parts[2]) if len(parts) == 3 else 0.0
            return week_dow_sod_to_datetime(_integer_text(parts[0], "Week"),
                                            _integer_text(parts[1], "DOW"), sod, epoch)
    except OverflowError as err:
        raise ValueError("Time is outside the supported range (years 1–9999).") from err
    raise ValueError("Unsupported format.")


def join_parts(key, vals):
    fields = [caption for row in SPLIT_FORM[key] for caption, _, _ in row]
    vals = [v.strip() for v in vals]
    if len(vals) > len(fields):
        raise ValueError("Too many fields.")
    vals += [""] * (len(fields) - len(vals))
    if not any(vals):
        return ""
    for field, value in zip(fields, vals):
        if any(char.isspace() for char in value):
            raise ValueError(f"{field} must contain a single value.")
    if key == "cal":
        required = range(6) if any(vals[3:]) else range(3)
    else:
        required_count = {"ydoy": 2, "mjdsod": 1, "mjdf": 1,
                          "weeksow": 2, "weekdow": 2}[key]
        required = range(required_count)
    for index in required:
        if not vals[index]:
            raise ValueError(f"{fields[index]} is required.")
    if key == "cal":
        date = "-".join(vals[:3])
        return date + " " + ":".join(vals[3:]) if any(vals[3:]) else date
    while vals and not vals[-1]:
        vals.pop()
    return " ".join(vals)


def split_parts(key, value):
    n = sum(len(row) for row in SPLIT_FORM[key])
    value = (value or "").strip()
    if not value or value in ("-", "—"):
        return [""] * n
    if key == "cal":
        try:
            parts = value.replace("/", "-").split()
            _field_count(parts, 1, 2, "YYYY-MM-DD [HH:MM:SS]")
            y, mo, da = parts[0].split("-")
            h, mi, s = parts[1].split(":") if len(parts) == 2 else ("", "", "")
            return [y, mo, da, h, mi, s]
        except ValueError:
            # Keep an invalid draft intact rather than silently discarding it.
            return [value] + [""] * (n - 1)
    tokens = value.split()
    if len(tokens) > n:
        return [value] + [""] * (n - 1)
    return tokens + [""] * (n - len(tokens))
