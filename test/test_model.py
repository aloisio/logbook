import datetime
import re
import shutil
from pathlib import Path
from typing import Callable

from model import Logbook, Year, Month, Day, ParseError, Footer, DayHeader

DATE_1 = datetime.date(2021, 8, 20)

DATE_2 = datetime.date(2021, 9, 19)

DAY_1_RELATIVE_PATH = '2021/08/20/20210820.md'

DAY_2_RELATIVE_PATH = '2021/09/19/20210919.md'

MONTH_1_RELATIVE_PATH = '2021/08/202108.md'

YEAR_RELATIVE_PATH = '2021/2021.md'

LOGBOOK_RELATIVE_PATH = 'index.md'

TEST_ROOT = Path(__file__).parent


class TestLogbook:
    def test_dataclass(self, tmp_path):
        logbook = Logbook(tmp_path)
        assert logbook.root == tmp_path
        assert logbook == Logbook(tmp_path)
        assert logbook < Logbook(tmp_path / 'subdir')
        assert logbook > Logbook(tmp_path.parent)

    def test_path(self, tmp_path):
        logbook = Logbook(tmp_path)
        assert logbook.path == tmp_path / 'index.md'

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        logbook = Logbook(logbook_path)
        result = logbook.parse()
        assert logbook.years == [Year(Day(logbook_path, DATE_1))]
        assert result.valid
        assert not result.errors


class TestYear:
    def test_dataclass(self, tmp_path):
        year1 = Year(Day(tmp_path, datetime.date(2020, 1, 1)))
        year2 = Year(Day(tmp_path, datetime.date(2019, 1, 1)))
        assert year1.root == year2.root == tmp_path
        assert year1.year == 2020
        assert year2.year == 2019
        assert year2 < year1
        assert year1 == Year(Day(tmp_path, datetime.date(2020, 12, 31)))

    def test_hashable(self, tmp_path):
        year1 = Year(Day(tmp_path, datetime.date(2020, 1, 1)))
        year2 = Year(Day(tmp_path, datetime.date(2020, 12, 31)))
        assert {year1, year2} == {Year(Day(tmp_path, datetime.date(2020, 8, 1)))}

    def test_path(self, tmp_path):
        year = Year(Day(tmp_path, datetime.date(2021, 1, 4)))
        assert year.path == tmp_path / '2021/2021.md'

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_1))
        assert year.months == [Month(Day(logbook_path, datetime.date(2021, 8, 20))),
                               Month(Day(logbook_path, datetime.date(2021, 9, 19)))]
        assert year.days == [Day(logbook_path, datetime.date(2021, 8, 20)),
                             Day(logbook_path, datetime.date(2021, 9, 19))]
        result = year.parse()
        assert result.valid
        assert not result.errors


class TestMonth:
    def test_dataclass(self, tmp_path):
        month1 = Month(Day(tmp_path, datetime.date(2021, 8, 20)))
        month2 = Month(Day(tmp_path, datetime.date(2019, 12, 1)))
        assert month1.root == month2.root == tmp_path
        assert month1.year == 2021
        assert month1.month == 8
        assert month2 < month1
        assert month1 == Month(Day(tmp_path, datetime.date(2021, 8, 31)))

    def test_hashable(self, tmp_path):
        month1 = Month(Day(tmp_path, datetime.date(2020, 8, 1)))
        month2 = Month(Day(tmp_path, datetime.date(2020, 8, 31)))
        assert {month1, month2} == {Month(Day(tmp_path, datetime.date(2020, 8, 8)))}

    def test_path(self, tmp_path):
        month = Month(Day(tmp_path, datetime.date(2021, 1, 4)))
        assert month.path == tmp_path / '2021/01/202101.md'

    def test_name(self, tmp_path):
        month = Month(Day(tmp_path, datetime.date(2021, 1, 4)))
        assert month.name == 'january'

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_1))
        result = month.parse()
        assert month.days == [Day(logbook_path, DATE_1)]
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

    def test_create_from_files(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        all_days = Day.create(logbook_path)
        assert all_days == [Day(logbook_path, DATE_1), Day(logbook_path, DATE_2)]
        assert all_days[0].previous is None
        assert all_days[1].previous == all_days[0]
        assert all_days[0].next == all_days[1]
        assert all_days[1].next is None

    def test_path(self, tmp_path):
        day = Day(tmp_path, datetime.date(2021, 1, 4))
        assert day.path == tmp_path / '2021/01/04/20210104.md'

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        day = Day(logbook_path, datetime.date(2021, 8, 20))
        result = day.parse()
        assert result.valid
        assert not result.errors

    def test_parse_invalid_file_does_not_exist(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        day = Day(logbook_path, datetime.date(2021, 8, 19))
        result = day.parse()
        assert ParseError(day.path, 'Markdown file does not exist') in result.errors

    def test_parse_invalid_missing_footer(self, tmp_path):
        def remove_footer(day_text):
            return re.sub(r'<footer.*?footer>', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_footer)
        day = Day(logbook_path, DATE_1)
        result = day.parse()
        assert ParseError(day.path, 'Missing footer') in result.errors


class TestDayHeader:
    def test_dataclass(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        header1 = DayHeader(Day(logbook_path, DATE_2))
        header2 = DayHeader(Day(logbook_path, DATE_1))
        assert header2 < header1
        assert header1 == DayHeader(Day(logbook_path, DATE_2))

    def test_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        header1 = DayHeader(Day(logbook_path, DATE_1))
        header2 = DayHeader(Day(logbook_path, DATE_2))
        assert not header1.parse().errors
        assert not header2.parse().errors

    def test_invalid_missing_h1(self, tmp_path):
        def remove_h1(day_text):
            return re.sub(r'^# .*?\n', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_h1)
        header = DayHeader(Day(logbook_path, DATE_1))
        assert ParseError(header.path, 'Missing header') in header.parse().errors

    def test_invalid_multiple_h1(self, tmp_path):
        def duplicate_h1(day_text):
            return re.sub(r'^(# .*?\n)', r'\1\1', day_text)

        logbook_path = create_logbook_files(tmp_path, duplicate_h1)
        header = DayHeader(Day(logbook_path, DATE_1))
        assert ParseError(header.path, 'Multiple headers') in header.parse().errors

    def test_invalid_h1_not_first_element(self, tmp_path):
        def move_h1_down(day_text):
            return re.sub(r'^(# .*?\n)', r'- Item\n\1', day_text)

        logbook_path = create_logbook_files(tmp_path, move_h1_down)
        header = DayHeader(Day(logbook_path, DATE_1))
        assert ParseError(header.path, 'Header is not first element') in header.parse().errors

    def test_template(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        day = Day(logbook_path, DATE_1)
        day.next = Day(logbook_path, DATE_2)
        header = DayHeader(day)
        assert header.template == '# ◀ [2021-08-20](../../2021.md#august) [▶](../../09/19/20210919.md)'


class TestFooter:
    def test_dataclass(self, tmp_path):
        footer1 = Footer(Day(tmp_path, DATE_2))
        footer2 = Footer(Day(tmp_path, DATE_1))
        assert footer2 < footer1
        assert footer1 == Footer(Day(tmp_path, DATE_2))

    def test_template_for_day(self, tmp_path):
        footer = Footer(Day(tmp_path, DATE_1))
        assert '=../../../style.css' in footer.template

    def test_template_for_month(self, tmp_path):
        footer = Footer(Month(Day(tmp_path, DATE_1)))
        assert '=../../style.css' in footer.template

    def test_template_for_year(self, tmp_path):
        footer = Footer(Year(Day(tmp_path, DATE_1)))
        assert '=../style.css' in footer.template

    def test_template_for_logbook(self, tmp_path):
        footer = Footer(Logbook(tmp_path))
        assert '=style.css' in footer.template

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        footer = Footer(Day(logbook_path, DATE_1))
        result = footer.parse()
        assert result.valid
        assert not result.errors

    def test_parse_invalid_missing_footer(self, tmp_path):
        def remove_footer(day_text):
            return re.sub(r'<footer.*?footer>', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_footer)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Missing footer') in footer.parse().errors

    def test_parse_invalid_multiple_footers(self, tmp_path):
        def add_footer(day_text):
            return day_text + '\n<footer><hr></footer>'

        logbook_path = create_logbook_files(tmp_path, add_footer)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Multiple footers') in footer.parse().errors

    def test_parse_invalid_footer_missing_rule(self, tmp_path):
        def remove_hr(day_text):
            return re.sub(r'<footer.*?footer>', '<footer></footer>', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_hr)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer is missing rule') in footer.parse().errors

    def test_parse_invalid_footer_multiple_rules(self, tmp_path):
        def duplicate_hr(day_text):
            return re.sub(r'(<hr[^>]*?>)', r'\1\1', day_text)

        logbook_path = create_logbook_files(tmp_path, duplicate_hr)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer has multiple rules') in footer.parse().errors

    def test_parse_invalid_footer_missing_stylesheet_link(self, tmp_path):
        def remove_link(day_text):
            return re.sub(r'<link[^>]*?>', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer is missing stylesheet link') in footer.parse().errors

    def test_parse_invalid_footer_has_link_rel_different_than_stylesheet(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'rel=stylesheet', 'rel=prefetch', day_text)

        logbook_path = create_logbook_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer is missing stylesheet link') in footer.parse().errors

    def test_parse_invalid_footer_has_multiple_links(self, tmp_path):
        def duplicate_link(day_text):
            return re.sub(r'(<link[^>]*?>)', r'\1\1', day_text)

        logbook_path = create_logbook_files(tmp_path, duplicate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer has multiple links') in footer.parse().errors

    def test_parse_invalid_footer_is_not_last_element(self, tmp_path):
        def add_content(day_text):
            return re.sub(r'(<footer.*?footer>)', r'\1<p>Finis</p>', day_text)

        logbook_path = create_logbook_files(tmp_path, add_content)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer is not last element') in footer.parse().errors


def create_logbook_files(root: Path, day_mutator: Callable[[str], str] = lambda s: s):
    logbook_path = root / 'logbook'
    shutil.copytree(TEST_ROOT / 'resources', logbook_path)
    day_path = logbook_path / DAY_1_RELATIVE_PATH
    day_path.write_text(day_mutator(day_path.read_text()))
    return logbook_path
