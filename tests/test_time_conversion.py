import datetime as dt
import random
import unittest

from src import time_conversion as time


class TimeScaleTests(unittest.TestCase):
    def test_known_epochs_and_current_offset(self):
        self.assertEqual(time.week_sow_to_datetime(0, 0, time.GPS_EPOCH), dt.datetime(1980, 1, 6))
        self.assertEqual(time.week_sow_to_datetime(0, 0, time.BDS_EPOCH), dt.datetime(2006, 1, 1))
        self.assertEqual(time.bdt_to_utc(time.BDS_EPOCH), time.BDS_EPOCH)
        utc = dt.datetime(2026, 10, 22, 12, 34, 56, 789123)
        self.assertEqual(time.utc_to_gpst(utc), utc + dt.timedelta(seconds=18))
        self.assertEqual(time.utc_to_bdt(utc), utc + dt.timedelta(seconds=4))

    def test_all_18_leap_second_intervals_are_rejected(self):
        self.assertEqual(len(time.GPS_UTC_OFFSETS), 18)
        for utc_boundary, new_offset in time.GPS_UTC_OFFSETS:
            gps_start = utc_boundary + dt.timedelta(seconds=new_offset - 1)
            for microseconds in (0, 1, 500000, 999999):
                gps = gps_start + dt.timedelta(microseconds=microseconds)
                with self.subTest(boundary=utc_boundary, microseconds=microseconds):
                    with self.assertRaisesRegex(ValueError, "leap second"):
                        time.gpst_to_utc(gps)
                    with self.assertRaisesRegex(ValueError, "leap second"):
                        time.bdt_to_utc(gps - dt.timedelta(seconds=14))

    def test_both_sides_of_every_leap_boundary_round_trip(self):
        for boundary, new_offset in time.GPS_UTC_OFFSETS:
            for delta, expected_offset in ((-1, new_offset - 1), (0, new_offset), (1, new_offset)):
                utc = boundary + dt.timedelta(microseconds=delta)
                with self.subTest(boundary=boundary, delta=delta):
                    gps = time.utc_to_gpst(utc)
                    bds = time.utc_to_bdt(utc)
                    self.assertEqual(gps - utc, dt.timedelta(seconds=expected_offset))
                    self.assertEqual(time.gpst_to_utc(gps), utc)
                    self.assertEqual(time.bdt_to_utc(bds), utc)

    def test_random_regular_instants_round_trip_in_all_systems(self):
        rng = random.Random(10022)
        for _ in range(250):
            utc = time.GPS_EPOCH + dt.timedelta(days=rng.randrange(45000),
                                               seconds=rng.randrange(86400),
                                               microseconds=rng.randrange(1000000))
            for system in ("UTC", "GPST", "BDT"):
                with self.subTest(utc=utc, system=system):
                    self.assertEqual(time.to_utc(system, time.from_utc(system, utc)), utc)

    def test_datetime_overflow_is_an_explicit_value_error(self):
        for convert, value in ((time.utc_to_gpst, dt.datetime.max),
                               (time.utc_to_bdt, dt.datetime.min),
                               (time.bdt_to_utc, dt.datetime.max)):
            with self.subTest(convert=convert.__name__):
                with self.assertRaisesRegex(ValueError, "supported range"):
                    convert(value)


class NumericFormatTests(unittest.TestCase):
    def test_common_and_leap_year_doy_limits(self):
        for year in (1900, 2025, 2100):
            with self.subTest(year=year):
                self.assertEqual(time.ydoy_sod_to_datetime(year, 365, 0), dt.datetime(year, 12, 31))
                with self.assertRaisesRegex(ValueError, "365"):
                    time.ydoy_sod_to_datetime(year, 366, 0)
        for year in (2000, 2024):
            self.assertEqual(time.ydoy_sod_to_datetime(year, 366, 0), dt.datetime(year, 12, 31))
        for doy in (0, -1, 367):
            with self.assertRaises(ValueError):
                time.ydoy_sod_to_datetime(2024, doy, 0)

    def test_mjd_known_values_and_negative_fraction(self):
        for mjd, expected in ((0, dt.datetime(1858, 11, 17)),
                              (-0.5, dt.datetime(1858, 11, 16, 12)),
                              (-1.25, dt.datetime(1858, 11, 15, 18)),
                              (51544.5, dt.datetime(2000, 1, 1, 12))):
            with self.subTest(mjd=mjd):
                self.assertEqual(time.mjd_float_to_datetime(mjd), expected)
                self.assertEqual(time.datetime_to_mjd_float(expected), mjd)

    def test_negative_week_with_positive_seconds_round_trips(self):
        for epoch in (time.GPS_EPOCH, time.BDS_EPOCH):
            date = epoch - dt.timedelta(microseconds=1000)
            self.assertEqual(time.datetime_to_week_sow(date, epoch), (-1, 604799.999))
            self.assertEqual(time.week_sow_to_datetime(-1, 604799.999, epoch), date)

    def test_seconds_bounds_and_nonfinite_values_are_rejected(self):
        for value in (-1, 86400, float("nan"), float("inf"), float("-inf")):
            calls = (
                lambda: time.ydoy_sod_to_datetime(2026, 1, value),
                lambda: time.mjd_sod_to_datetime(60000, value),
                lambda: time.week_dow_sod_to_datetime(0, 0, value, time.GPS_EPOCH),
            )
            for call in calls:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        call()
        for value in (-1, 604800, float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                time.week_sow_to_datetime(0, value, time.GPS_EPOCH)
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaisesRegex(ValueError, "finite"):
                time.mjd_float_to_datetime(value)

    def test_day_and_week_end_display_never_produces_out_of_range_seconds(self):
        original = dt.datetime(2026, 10, 24, 23, 59, 59, 999600)
        truncated = original.replace(microsecond=999000)
        expected = {
            "cal": "2026-10-24 23:59:59.999",
            "ydoy": "2026 297 86399.999",
            "mjdsod": "61337 86399.999",
            "weeksow": "2441 604799.999",
            "weekdow": "2441 6 86399.999",
        }
        for key, output in expected.items():
            with self.subTest(key=key):
                self.assertEqual(time.format_value("GPST", key, original), output)
                self.assertEqual(time.parse_value("GPST", key, output), truncated)

    def test_display_formats_share_millisecond_truncation(self):
        rng = random.Random(739)
        dates = [dt.datetime(2024, 12, 31, 23, 59, 59, 999999),
                 dt.datetime(1858, 11, 16, 23, 59, 59, 999999)]
        dates += [dt.datetime(1980, 1, 6) + dt.timedelta(days=rng.randrange(45000),
                                                       seconds=rng.randrange(86400),
                                                       microseconds=rng.randrange(1000000))
                  for _ in range(80)]
        for date in dates:
            truncated = date.replace(microsecond=date.microsecond // 1000 * 1000)
            for system in ("UTC", "GPST", "BDT"):
                for key, _, _ in time.FORMATS:
                    if system == "UTC" and key in time.WEEK_KEYS:
                        continue
                    with self.subTest(date=date, system=system, key=key):
                        display = time.format_value(system, key, date)
                        parsed = time.parse_value(system, key, display)
                        if key == "mjdf":
                            self.assertLessEqual(abs(parsed - truncated), dt.timedelta(microseconds=44))
                        else:
                            self.assertEqual(parsed, truncated)

    def test_calendar_format_pads_early_years(self):
        value = dt.datetime(1, 2, 3, 4, 5, 6, 7000)
        text = time.format_value("UTC", "cal", value)
        self.assertEqual(text, "0001-02-03 04:05:06.007")
        self.assertEqual(time.parse_value("UTC", "cal", text), value)


class ParserTests(unittest.TestCase):
    def test_optional_time_and_sod_are_zero(self):
        cases = (("UTC", "cal", "2026/10/22", dt.datetime(2026, 10, 22)),
                 ("UTC", "ydoy", "2026 1", dt.datetime(2026, 1, 1)),
                 ("UTC", "mjdsod", "0", time.MJD_EPOCH),
                 ("GPST", "weekdow", "0 0", time.GPS_EPOCH))
        for system, key, text, expected in cases:
            with self.subTest(key=key):
                self.assertEqual(time.parse_value(system, key, text), expected)

    def test_extra_fields_are_not_ignored(self):
        cases = (("cal", "2026-10-22 00:00:00 garbage"),
                 ("ydoy", "2026 1 0 garbage"),
                 ("mjdsod", "60000 0 garbage"),
                 ("mjdf", "60000.5 garbage"),
                 ("weeksow", "2000 0 garbage"),
                 ("weekdow", "2000 0 0 garbage"))
        for key, text in cases:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "Expected"):
                    time.parse_value("GPST", key, text)

    def test_fractional_integer_fields_are_not_truncated(self):
        for key, text in (("ydoy", "2026.0 1"), ("ydoy", "2026 1.5"),
                          ("mjdsod", "60000.5 0"), ("mjdsod", "60000.0 0"),
                          ("weeksow", "2000.5 0"), ("weekdow", "2000 1.5 0")):
            with self.subTest(key=key, text=text):
                with self.assertRaisesRegex(ValueError, "integer"):
                    time.parse_value("GPST", key, text)

    def test_nonfinite_input_is_rejected_in_all_numeric_formats(self):
        for value in ("NaN", "inf", "-inf", "1e999"):
            for key, text in (("ydoy", f"2026 1 {value}"),
                              ("mjdsod", f"60000 {value}"), ("mjdf", value),
                              ("weeksow", f"2000 {value}"), ("weekdow", f"2000 0 {value}")):
                with self.subTest(key=key, value=value):
                    with self.assertRaisesRegex(ValueError, "finite"):
                        time.parse_value("GPST", key, text)

    def test_missing_and_invalid_input_is_rejected(self):
        for key, text in (("cal", ""), ("cal", "2026-02-30"),
                          ("cal", "2016-12-31 23:59:60"),
                          ("ydoy", "2026"), ("weeksow", "2000"),
                          ("weekdow", "2000 7 0"), ("mjdf", "garbage")):
            with self.subTest(key=key, text=text):
                with self.assertRaises(ValueError):
                    time.parse_value("GPST", key, text)
        with self.assertRaises(ValueError):
            time.parse_value("UTC", "weeksow", "0 0")
        with self.assertRaises(ValueError):
            time.parse_value("unknown", "cal", "2026-10-22")


class SplitFieldTests(unittest.TestCase):
    def test_all_blank_fields_produce_empty_input(self):
        for key, rows in time.SPLIT_FORM.items():
            with self.subTest(key=key):
                self.assertEqual(time.join_parts(key, [" "] * sum(map(len, rows))), "")
                self.assertEqual(time.join_parts(key, []), "")

    def test_missing_required_fields_do_not_shift_later_values(self):
        cases = (("cal", ["2026", "", "22", "", "", ""], "Month"),
                 ("cal", ["2026", "10", "22", "12", "", "00"], "Min"),
                 ("cal", ["2026", "10", "22", "", "00", "00"], "Hour"),
                 ("ydoy", ["2026", "", "123"], "DOY"),
                 ("mjdsod", ["", "123"], "MJD"),
                 ("weeksow", ["2000", ""], "SOW"),
                 ("weekdow", ["2000", "", "123"], "DOW"))
        for key, values, missing in cases:
            with self.subTest(key=key, values=values):
                with self.assertRaisesRegex(ValueError, missing):
                    time.join_parts(key, values)

    def test_optional_split_fields_match_single_field_input(self):
        for key, values, expected in (("cal", ["2026", "10", "22", "", "", ""], "2026-10-22"),
                                      ("ydoy", ["2026", "1", ""], "2026 1"),
                                      ("mjdsod", ["60000", ""], "60000"),
                                      ("weekdow", ["2000", "1", ""], "2000 1")):
            with self.subTest(key=key):
                self.assertEqual(time.join_parts(key, values), expected)
                self.assertEqual(time.join_parts(key, time.split_parts(key, expected)), expected)

    def test_valid_display_survives_split_and_join(self):
        date = dt.datetime(2026, 10, 22, 12, 34, 56, 789000)
        for key, _, _ in time.FORMATS:
            with self.subTest(key=key):
                value = time.format_value("GPST", key, date)
                self.assertEqual(time.join_parts(key, time.split_parts(key, value)), value)

    def test_split_mode_does_not_discard_invalid_extra_tokens(self):
        for key, text in (("cal", "2026-10-22 00:00:00 garbage"),
                          ("mjdsod", "60000 0 garbage")):
            with self.subTest(key=key):
                parts = time.split_parts(key, text)
                self.assertEqual(parts[0], text)
                with self.assertRaises(ValueError):
                    time.join_parts(key, parts)
        with self.assertRaisesRegex(ValueError, "single value"):
            time.join_parts("ydoy", ["2026 1", "2", "3"])
        with self.assertRaisesRegex(ValueError, "Too many"):
            time.join_parts("mjdf", ["60000", "1"])


if __name__ == "__main__":
    unittest.main()
