import datetime
import re
import shutil
from pathlib import Path
from typing import Callable

from model import Logbook, Year, Month, Day, ParseError, Footer, DayHeader, parse_markdown, parse_markdown_element

DATE_1 = datetime.date(2020, 8, 20)

DATE_2 = datetime.date(2021, 8, 20)

DATE_3 = datetime.date(2021, 9, 19)

DAY_1_RELATIVE_PATH = '2020/08/20/20200820.md'

MONTH_1_RELATIVE_PATH = '2020/08/202008.md'

YEAR_1_RELATIVE_PATH = '2020/2020.md'

YEAR_2_RELATIVE_PATH = '2021/2021.md'

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
        assert logbook.years == [Year(Day(logbook_path, DATE_1)), Year(Day(logbook_path, DATE_2))]
        assert result.valid
        assert not result.errors
        assert (logbook_path / 'index.md').exists(), 'Should create index'

    def test_parse_valid_creates_footer(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        logbook = Logbook(logbook_path)
        assert not logbook.parse().errors
        assert not Footer(logbook).parse().errors, 'Should create valid footer'

    def test_parse_invalid_missing_stylesheet(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        (logbook_path / 'style.css').unlink()
        result = Logbook(logbook_path).parse()
        assert ParseError(logbook_path, 'Missing style.css') in result.errors


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

    def test_create_from_files(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        all_years = Year.create(logbook_path)
        assert all_years == [Year(Day(logbook_path, DATE_1)), Year(Day(logbook_path, DATE_2))]
        assert all_years[0].previous is None
        assert all_years[1].previous == all_years[0]
        assert all_years[0].next == all_years[1]
        assert all_years[1].next is None

    def test_path(self, tmp_path):
        year = Year(Day(tmp_path, DATE_1))
        assert year.path == tmp_path / YEAR_1_RELATIVE_PATH

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_2))
        assert year.months == [Month(Day(logbook_path, DATE_2)),
                               Month(Day(logbook_path, DATE_3))]
        assert year.days == [Day(logbook_path, DATE_2),
                             Day(logbook_path, DATE_3)]
        assert year.days[0].next == year.days[1]
        assert year.days[1].previous == year.days[0]
        result = year.parse()
        assert result.valid
        assert not result.errors
        assert (logbook_path / YEAR_2_RELATIVE_PATH).exists(), 'Should create year summary'

    def test_parse_valid_creates_footer(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_1))
        assert not year.parse().errors
        assert not Footer(year).parse().errors, 'Should create valid footer'

    def test_parse_valid_creates_calendar_table(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_1))
        year.next = Year(Day(logbook_path, DATE_2))
        assert not year.parse().errors
        tree = parse_markdown(year.path)
        table = tree[0]
        assert table.tag == 'table', 'Calendar table is first element'
        assert table.attrib['class'] == 'year'
        assert not set(table.attrib.keys()).intersection({'border', 'cellpadding', 'cellspacing'})
        for t in table.findall('.//table'):
            assert not set(t.attrib.keys()).intersection({'border', 'cellpadding', 'cellspacing'})
            assert ''.join(list(t.iter('tr'))[1].text_content().split()) == 'MoTuWeThFrSaSu'
        assert not list(filter(None, [c.attrib.get('class', None) for c in table.iter('td', 'th')]))
        month_links = table.findall('.//a')
        assert month_links[0].text == '2020'
        assert month_links[0].attrib['href'] == '../index.md'
        assert month_links[1].text == '▶'
        assert month_links[1].attrib['href'] == '../2021/2021.md'
        assert month_links[2].text == 'August'
        assert month_links[2].attrib['href'] == '08/202008.md'
        assert month_links[3].text == '20'
        assert month_links[3].attrib['href'] == '08/20/20200820.md'
        month_ids = list(filter(None, map(lambda e: e.attrib.get('id', None), table.findall('.//table/..'))))
        assert ['august'] == month_ids

    def test_parse_invalid_missing_day_header(self, tmp_path):
        def remove_header(day_text):
            return re.sub(r'^# .*?\n', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_header)
        day = Day(logbook_path, DATE_1)
        result = Year(day).parse()
        assert ParseError(day.path, 'Missing header') in result.errors


class TestMonth:
    def test_dataclass(self, tmp_path):
        month1 = Month(Day(tmp_path, datetime.date(2021, 8, 20)))
        month2 = Month(Day(tmp_path, datetime.date(2019, 12, 1)))
        assert month1.root == month2.root == tmp_path
        assert month1.year == 2021
        assert month1.month == 8
        assert month2 < month1
        assert month1 == Month(Day(tmp_path, datetime.date(2021, 8, 31)))

    def test_equals(self, tmp_path):
        month1 = Month(Day(tmp_path, DATE_1))
        month2 = Month(Day(tmp_path, DATE_1))
        month3 = Month(Day(tmp_path, DATE_2))
        month2.next = month3
        assert month1 == month2

    def test_hashable(self, tmp_path):
        month1 = Month(Day(tmp_path, datetime.date(2020, 8, 1)))
        month2 = Month(Day(tmp_path, datetime.date(2020, 8, 31)))
        assert {month1, month2} == {Month(Day(tmp_path, datetime.date(2020, 8, 8)))}

    def test_path(self, tmp_path):
        month = Month(Day(tmp_path, DATE_1))
        assert month.path == tmp_path / MONTH_1_RELATIVE_PATH

    def test_name(self, tmp_path):
        month = Month(Day(tmp_path, datetime.date(2021, 1, 4)))
        assert month.name == 'january'

    def test_create_from_files(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        all_months = Month.create(logbook_path)
        assert all_months == [Month(Day(logbook_path, DATE_1)), Month(Day(logbook_path, DATE_2)),
                              Month(Day(logbook_path, DATE_3))]
        assert all_months[0].previous is None
        assert all_months[1].previous == all_months[0]
        assert all_months[2].previous == all_months[1]
        assert all_months[0].next == all_months[1]
        assert all_months[1].next == all_months[2]
        assert all_months[2].next is None

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_1))
        result = month.parse()
        assert month.days == [Day(logbook_path, DATE_1)]
        assert result.valid
        assert not result.errors
        assert (logbook_path / MONTH_1_RELATIVE_PATH).exists(), 'Should create month summary'

    def test_parse_valid_creates_footer(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_1))
        assert not month.parse().errors
        assert not Footer(month).parse().errors, 'Should create valid footer'

    def test_parse_valid_creates_calendar_table(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_1))
        month.next = Month(Day(logbook_path, DATE_2))
        assert not month.parse().errors
        tree = parse_markdown(month.path)
        table = tree[0]
        assert table.tag == 'table', 'Calendar table is first element'
        assert table.attrib['class'] == 'month'
        assert not set(table.attrib.keys()).intersection({'border', 'cellpadding', 'cellspacing'})
        assert not list(filter(None, [c.attrib.get('class', None) for c in table.iter('td', 'th')]))
        assert ''.join(list(table.iter('tr'))[1].text_content().split()) == 'MoTuWeThFrSaSu'
        month_links = table.findall('.//a')
        assert month_links[0].text == '2020-08'
        assert month_links[0].attrib['href'] == '../2020.md#august'
        assert month_links[1].text == '▶'
        assert month_links[1].attrib['href'] == '../../2021/08/202108.md'
        assert month_links[2].text == '20'
        assert month_links[2].attrib['href'] == '20/20200820.md'


class TestDay:
    def test_dataclass(self, tmp_path):
        day1 = Day(tmp_path, DATE_2)
        day2 = Day(tmp_path, DATE_1)
        assert day1.root == day2.root == tmp_path
        assert day1.year == 2021
        assert day1.month == 8
        assert day1.day == 20
        assert day2 < day1
        assert day1 == Day(tmp_path, DATE_2)

    def test_create_from_files(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        all_days = Day.create(logbook_path)
        assert all_days == [Day(logbook_path, DATE_1), Day(logbook_path, DATE_2), Day(logbook_path, DATE_3)]
        assert all_days[0].previous is None
        assert all_days[1].previous == all_days[0]
        assert all_days[2].previous == all_days[1]
        assert all_days[0].next == all_days[1]
        assert all_days[1].next == all_days[2]
        assert all_days[2].next is None

    def test_path(self, tmp_path):
        day = Day(tmp_path, DATE_1)
        assert day.path == tmp_path / DAY_1_RELATIVE_PATH

    def test_parse_valid(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        day = Day(logbook_path, DATE_2)
        day.previous = Day(logbook_path, DATE_1)
        day.next = Day(logbook_path, DATE_3)
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
        day1 = Day(logbook_path, DATE_1)
        day2 = Day(logbook_path, DATE_2)
        day3 = Day(logbook_path, DATE_3)
        day1.next = day2
        day2.previous = day1
        day2.next = day3
        day3.previous = day2
        header1 = DayHeader(day1)
        header2 = DayHeader(day2)
        header3 = DayHeader(day3)
        assert not header1.parse().errors
        assert not header2.parse().errors
        assert not header3.parse().errors

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

    def test_invalid_h1_content(self, tmp_path):
        def invalidate_header(day_text):
            return re.sub(r'^\(\.\.', '(.', day_text)

        logbook_path = create_logbook_files(tmp_path, invalidate_header)
        header = DayHeader(Day(logbook_path, DATE_1))
        assert ParseError(header.path, 'Header content problem') in header.parse().errors

    def test_template(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        day = Day(logbook_path, DATE_1)
        day.next = Day(logbook_path, DATE_2)
        header = DayHeader(day)
        assert header.template == '# ◀ [2020-08-20](../../2020.md#august) [▶](../../../2021/08/20/20210820.md)'


class TestMonthHeader:
    def test_template_only_month(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_1))
        assert not month.parse().errors
        th = parse_markdown_element(month.header.template)
        assert th.text_content() == '◀ 2020-08 ▶'
        assert th.attrib['colspan'] == '7'
        a = next(th.iter('a'), None)
        assert a is not None
        assert a.text_content() == '2020-08'
        assert a.attrib['href'] == '../2020.md#august'

    def test_template_middle_month(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        month = Month(Day(logbook_path, DATE_2))
        month.previous = Month(Day(logbook_path, DATE_1))
        month.next = Month(Day(logbook_path, DATE_3))
        assert not month.parse().errors
        th = parse_markdown_element(month.header.template)
        assert th.text_content() == '◀ 2021-08 ▶'
        assert th.attrib['colspan'] == '7'
        a = list(th.iter('a'))
        assert len(a) == 3
        assert a[0].text_content() == '◀'
        assert a[0].attrib['href'] == '../../2020/08/202008.md'
        assert a[1].text_content() == '2021-08'
        assert a[1].attrib['href'] == '../2021.md#august'
        assert a[2].text_content() == '▶'
        assert a[2].attrib['href'] == '../09/202109.md'


class TestYearHeader:
    def test_template_only_year(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_1))
        assert not year.parse().errors
        th = parse_markdown_element(year.header.template)
        assert th.text_content() == '◀ 2020 ▶'
        assert th.attrib['colspan'] == '3'
        assert len(links := th.findall('.//a')) == 1
        assert links[0].text == '2020'
        assert links[0].attrib['href'] == '../index.md'

    def test_template_middle_year(self, tmp_path):
        logbook_path = create_logbook_files(tmp_path)
        year = Year(Day(logbook_path, DATE_2))
        year.previous = Year(Day(logbook_path, DATE_1))
        year.next = Year(Day(logbook_path, datetime.date(2022, 1, 1)))
        assert not year.parse().errors
        th = parse_markdown_element(year.header.template)
        assert th.text_content() == '◀ 2021 ▶'
        assert th.attrib['colspan'] == '3'
        assert len(links := th.findall('.//a')) == 3
        assert links[0].text == '◀'
        assert links[0].attrib['href'] == '../2020/2020.md'
        assert links[1].text == '2021'
        assert links[1].attrib['href'] == '../index.md'
        assert links[2].text == '▶'
        assert links[2].attrib['href'] == '../2022/2022.md'


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
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_multiple_rules(self, tmp_path):
        def duplicate_hr(day_text):
            return re.sub(r'(<hr[^>]*?>)', r'\1\1', day_text)

        logbook_path = create_logbook_files(tmp_path, duplicate_hr)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_missing_stylesheet_link(self, tmp_path):
        def remove_link(day_text):
            return re.sub(r'<link[^>]*?>', '', day_text)

        logbook_path = create_logbook_files(tmp_path, remove_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_has_link_rel_different_than_stylesheet(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'rel=stylesheet', 'rel=prefetch', day_text)

        logbook_path = create_logbook_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_wrong_link_href(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'href=../../../style.css', 'href=style.css', day_text)

        logbook_path = create_logbook_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_missing_link_href(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'href=../../../style.css', '', day_text)

        logbook_path = create_logbook_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_footer_has_multiple_links(self, tmp_path):
        def duplicate_link(day_text):
            return re.sub(r'(<link[^>]*?>)', r'\1\1', day_text)

        logbook_path = create_logbook_files(tmp_path, duplicate_link)
        footer = Footer(Day(logbook_path, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

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
