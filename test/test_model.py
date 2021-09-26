import datetime
import shutil
from pathlib import Path

from model import Logbook, Year, Month, Day

TEST_ROOT = Path(__file__).parent


class TestLogbook:
    def test_dataclass(self, tmp_path):
        logbook = Logbook(tmp_path)
        assert logbook.root == tmp_path
        assert logbook == Logbook(tmp_path)
        assert logbook < Logbook(tmp_path / 'subdir')
        assert logbook > Logbook(tmp_path.parent)

    def test_parse_valid(self, tmp_path):
        logbook_path = tmp_path / 'logbook'
        shutil.copytree(TEST_ROOT / 'resources', logbook_path)
        result = Logbook(logbook_path).parse()
        assert result.valid
        assert not result.errors


class TestYear:
    def test_dataclass(self, tmp_path):
        year1 = Year(tmp_path, datetime.date(2020, 1, 1))
        year2 = Year(tmp_path, datetime.date(2019, 1, 1))
        assert year1.root == year2.root == tmp_path
        assert year1.year == 2020
        assert year2.year == 2019
        assert year2 < year1
        assert year1 == Year(tmp_path, datetime.date(2020, 12, 31))

    def test_parse_valid(self, tmp_path):
        logbook_path = tmp_path / 'logbook'
        shutil.copytree(TEST_ROOT / 'resources', logbook_path)
        result = Year(logbook_path, datetime.date(2021, 8, 19)).parse()
        assert result.valid
        assert not result.errors


class TestMonth:
    def test_dataclass(self, tmp_path):
        month1 = Month(tmp_path, datetime.date(2021, 8, 20))
        month2 = Month(tmp_path, datetime.date(2019, 12, 1))
        assert month1.root == month2.root == tmp_path
        assert month1.year == 2021
        assert month1.month == 8
        assert month2 < month1
        assert month1 == Month(tmp_path, datetime.date(2021, 8, 31))

    def test_parse_valid(self, tmp_path):
        logbook_path = tmp_path / 'logbook'
        shutil.copytree(TEST_ROOT / 'resources', logbook_path)
        result = Month(logbook_path, datetime.date(2021, 8, 19)).parse()
        assert result.valid
        assert not result.errors


class TestDay:
    def test_dataclass(self, tmp_path):
        day1 = Day(tmp_path, datetime.date(2021, 8, 20))
        day2 = Day(tmp_path, datetime.date(2019, 12, 1))
        assert day1.root == day2.root == tmp_path
        assert day1.year == 2021
        assert day1.month == 8
        assert day1.day == 20
        assert day2 < day1
        assert day1 == Day(tmp_path, datetime.date(2021, 8, 20))

    def test_parse_valid(self, tmp_path):
        logbook_path = tmp_path / 'logbook'
        shutil.copytree(TEST_ROOT / 'resources', logbook_path)
        result = Day(logbook_path, datetime.date(2021, 8, 19)).parse()
        assert result.valid
        assert not result.errors
