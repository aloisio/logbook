import datetime
import re
import shutil
from pathlib import Path
from textwrap import dedent
from typing import Callable

import pytest
from lxml.html import document_fromstring

from model import Logbook, Year, Month, Day, ParseError, Footer, DayHeader, MarkdownParser

DATE_1 = datetime.date(2020, 8, 20)

DATE_2 = datetime.date(2021, 8, 20)

DATE_3 = datetime.date(2021, 9, 19)

DAY_1_RELATIVE_PATH = '2020/08/20/20200820.md'

MONTH_1_RELATIVE_PATH = '2020/08/202008.md'

TEST_ROOT = Path(__file__).parent


class TestLogbook:
    def test_dataclass(self, tmp_path):
        logbook = Logbook(tmp_path)
        assert logbook.root == tmp_path
        assert logbook == Logbook(tmp_path)
        assert logbook != Logbook(tmp_path / 'subdir')

    def test_path(self, tmp_path):
        logbook = Logbook(tmp_path)
        assert logbook.path == tmp_path / 'index.md'

    def test_find_day_by_date(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        assert logbook.day(DATE_2) == logbook.years[1].days[0]
        assert logbook.day(datetime.date(2020, 8, 8)) is None

    def test_parse_valid(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert (result := logbook.parse()).valid
        assert not result.errors
        assert logbook.years == [Year(Day(logbook.root, DATE_1)),
                                 Year(Day(logbook.root, DATE_2))]
        assert logbook.years[0].next == logbook.years[1]
        assert logbook.years[1].previous == logbook.years[0]
        assert logbook.path.exists(), 'Should create index'

    def test_parse_valid_creates_footer(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert not logbook.parse().errors
        assert not logbook.footer.parse().errors, 'Should create valid footer'

    def test_parse_valid_creates_year_links(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert not logbook.parse().errors
        tree = MarkdownParser.markdown_to_html_document(logbook.path)
        links = list(tree.iterlinks())[:-1]
        assert links[0][0].text == '2020'
        assert links[0][2] == '2020/2020.md'
        assert links[1][0].text == '2021'
        assert links[1][2] == '2021/2021.md'

    def test_parse_valid_creates_linked_years(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert not logbook.parse().errors
        all_years = logbook.years
        assert all_years == [Year(Day(logbook.root, DATE_1)),
                             Year(Day(logbook.root, DATE_2))]
        assert all_years[0].previous is None
        assert all_years[1].previous == all_years[0]
        assert all_years[0].next == all_years[1]
        assert all_years[1].next is None

    def test_parse_valid_creates_year_summaries(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        year = logbook.years[1]
        assert year.months == [Month(Day(logbook.root, DATE_2)),
                               Month(Day(logbook.root, DATE_3))]
        assert year.days == [Day(logbook.root, DATE_2),
                             Day(logbook.root, DATE_3)]
        assert year.days[0].next[''] == year.days[1]
        assert year.days[1].previous[''] == year.days[0]
        result = year.parse()
        assert result.valid
        assert not result.errors
        assert (logbook.root / '2021' / '2021.md').exists(), 'Should create year summary'

    def test_parse_valid_creates_year_summary_footer(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        year = logbook.years[0]
        assert not year.parse().errors
        assert not Footer(year).parse().errors, 'Should create valid footer'

    def test_parse_valid_creates_year_calendar_table(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        year = logbook.years[0]
        assert not year.parse().errors
        tree = MarkdownParser.markdown_to_html_document(year.path)
        table = tree[0][0]
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
        assert month_links[1].text == '❯'
        assert month_links[1].attrib['href'] == '../2021/2021.md'
        assert month_links[2].text == 'August'
        assert month_links[2].attrib['href'] == '08/202008.md'
        assert month_links[3].text == '20'
        assert month_links[3].attrib['href'] == '08/20/20200820.md'
        month_ids = list(filter(None, map(lambda e: e.attrib.get('id', None), table.findall('.//table'))))
        assert ['august'] == month_ids

    def test_parse_valid_creates_linked_months(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert not logbook.parse().errors
        all_months = [m for y in logbook.years for m in y.months]
        assert all_months == [Month(Day(logbook.root, DATE_1)),
                              Month(Day(logbook.root, DATE_2)),
                              Month(Day(logbook.root, DATE_3))]
        assert all_months[0].previous is None
        assert all_months[1].previous == all_months[0]
        assert all_months[2].previous == all_months[1]
        assert all_months[0].next == all_months[1]
        assert all_months[1].next == all_months[2]
        assert all_months[2].next is None

    def test_parse_valid_creates_month_summaries(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        month = logbook.years[0].months[0]
        result = month.parse()
        assert month.days == [Day(logbook.root, DATE_1)]
        assert result.valid
        assert not result.errors
        assert (logbook.root / MONTH_1_RELATIVE_PATH).exists(), 'Should create month summary'

    def test_parse_valid_creates_month_footer(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        month = logbook.years[0].months[0]
        assert not month.parse().errors
        assert not Footer(month).parse().errors, 'Should create valid footer'

    def test_parse_valid_creates_month_calendar_table(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        month = logbook.years[0].months[0]
        assert not month.parse().errors
        tree = MarkdownParser.markdown_to_html_document(month.path)
        table = tree[0][0]
        assert table.tag == 'table', 'Calendar table is first element'
        assert table.attrib['class'] == 'month'
        assert not set(table.attrib.keys()).intersection({'border', 'cellpadding', 'cellspacing'})
        assert not list(filter(None, [c.attrib.get('class', None) for c in table.iter('td', 'th')]))
        assert ''.join(list(table.iter('tr'))[1].text_content().split()) == 'MoTuWeThFrSaSu'
        month_links = table.findall('.//a')
        assert month_links[0].text == '2020-08'
        assert month_links[0].attrib['href'] == '../2020.md#august'
        assert month_links[1].text == '❯'
        assert month_links[1].attrib['href'] == '../../2021/08/202108.md'
        assert month_links[2].text == '20'
        assert month_links[2].attrib['href'] == '20/20200820.md'

    def test_parse_valid_day_links(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert not logbook.parse().errors
        days = [d for y in logbook.years for d in y.days]
        assert days == [d for y in logbook.years for m in y.months for d in m.days]
        assert days == [Day(logbook.root, DATE_1),
                        Day(logbook.root, DATE_2),
                        Day(logbook.root, DATE_3)]

        assert '' not in days[0].previous
        assert days[0].next[''] is days[1]
        assert days[1].previous[''] is days[0]
        assert days[1].next[''] is days[2]
        assert days[2].previous[''] is days[1]
        assert '' not in days[2].next

        assert 'thread' not in days[0].previous
        assert days[0].next['thread'] is days[2]
        assert 'thread' not in days[1].previous
        assert 'thread' not in days[1].next
        assert days[2].previous['thread'] is days[0]
        assert 'thread' not in days[2].next

        assert 'lorem' not in days[0].previous
        assert 'lorem' not in days[0].next
        assert 'lorem' not in days[1].previous
        assert 'lorem' not in days[1].next
        assert 'lorem' not in days[2].previous
        assert 'lorem' not in days[2].next

    def test_parse_valid_day_ids(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        assert logbook.parse().valid
        assert logbook.years[0].days[0].ids == ['thread', 'lorem']
        assert logbook.years[1].days[0].ids == []
        assert logbook.years[1].days[1].ids == ['thread']

    def test_parse_valid_day_headers(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        logbook.parse()
        day1 = logbook.years[0].days[0]
        day2 = logbook.years[1].days[0]
        day3 = logbook.years[1].days[1]
        assert len(day1.headers) == 2
        assert day1.headers[0].level == 1
        assert day1.headers[0].xpath == '/html/body/h1'
        assert day1.headers[0].ids == []
        assert day1.headers[1].level == 2
        assert day1.headers[1].xpath == '/html/body/h2'
        assert day1.headers[1].ids == ['thread']
        assert len(day2.headers) == 2
        assert len(day3.headers) == 3

    def test_parse_valid_day_footer(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        footer = Footer(Day(logbook.root, DATE_1))
        result = footer.parse()
        assert result.valid
        assert not result.errors

    def test_parse_invalid_missing_stylesheet(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        (logbook.root / 'style.css').unlink()
        assert ParseError(logbook.root, 'Missing style.css') in logbook.parse().errors

    def test_parse_invalid_markdown_is_not_utf_8(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        day_path = logbook.root / DAY_1_RELATIVE_PATH
        day_path.read_bytes()
        day_path.write_bytes(day_path.read_bytes().replace(b'Thread', b'ZS \x97 B'))
        errors = logbook.parse().errors
        assert ParseError(day_path, 'Markdown file encoding is not UTF-8') in errors

    def test_parse_invalid_markdown_contains_inline_links(self, tmp_path):
        def inline_link(day_text):
            inlined = re.sub(r'\[❯]\[2]', '[❯](../../../2021/08/20/20210820.md)', day_text)
            return re.sub(r'\[2]: .*?\n', '', inlined)

        logbook = create_logbook_from_files(tmp_path, inline_link)
        errors = logbook.parse().errors
        path = logbook.root / DAY_1_RELATIVE_PATH
        assert ParseError(path, 'Markdown file contains inline links') in errors

    def test_parse_invalid_day_file_does_not_exist(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        day = Day(logbook.root, datetime.date(2021, 8, 19))
        result = day.parse()
        assert ParseError(day.path, 'Markdown file does not exist') in result.errors

    def test_parse_invalid_day_empty_directory(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        day = Day(logbook.root, DATE_1)
        day.path.unlink()
        assert ParseError(day.path.parent, 'Empty directory') in logbook.parse().errors

    def test_parse_invalid_day_missing_h1(self, tmp_path):
        def remove_header(day_text):
            return re.sub(r'^# .*?\n', '', day_text)

        logbook = create_logbook_from_files(tmp_path, remove_header)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'Missing H1 header') in errors

    def test_parse_invalid_day_multiple_h1(self, tmp_path):
        def duplicate_h1(day_text):
            return re.sub(r'^(# .*?\n)', r'\1\1', day_text)

        logbook = create_logbook_from_files(tmp_path, duplicate_h1)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'Multiple H1 headers') in errors

    def test_parse_invalid_day_h2_has_multiple_ids(self, tmp_path):
        def add_id_to_h2(day_text):
            return re.sub(r'\n(## .*?)\n', r'\n\1 <wbr id=some_id>\n', day_text)

        logbook = create_logbook_from_files(tmp_path, add_id_to_h2)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'Multiple H2 ids: thread, some_id') in errors

    def test_parse_invalid_day_missing_footer(self, tmp_path):
        def remove_footer(day_text):
            return re.sub(r'<footer.*?footer>', '', day_text)

        logbook = create_logbook_from_files(tmp_path, remove_footer)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'Missing footer') in errors

    def test_parse_invalid_day_multiple_footers(self, tmp_path):
        def add_footer(day_text):
            return day_text + '\n<footer><hr></footer>'

        logbook = create_logbook_from_files(tmp_path, add_footer)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'Multiple footers') in errors

    def test_parse_invalid_day_h1_not_first_element(self, tmp_path):
        def move_h1_down(day_text):
            return re.sub(r'^(# .*?\n)', r'- Item\n\1', day_text)

        logbook = create_logbook_from_files(tmp_path, move_h1_down)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H1 header is not first element') in errors

    def test_invalid_day_h1_content(self, tmp_path):
        def invalidate_header(day_text):
            return re.sub(r'❮', '', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_header)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H1 header content problem') in errors

    def test_invalid_day_h2_wrong_pointers(self, tmp_path):
        def invalidate_h2(day_text):
            return re.sub(r'\n## ❮', '\n## <', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_h2)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H2 header pointer problem') in errors

    def test_invalid_day_h2_pointer_without_id(self, tmp_path):
        def invalidate_h2(day_text):
            return re.sub(r'\n(## .*?)\n', r'\n\1\n### ❮ Dangling Pointers ❯\n', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_h2)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H3 header has pointer but no ID') in errors

    def test_invalid_day_h2_missing_links(self, tmp_path):
        def invalidate_h2(day_text):
            return re.sub(r'\n## .*?\n', r'\n## ❮ Thread ❯ <wbr id=thread>\n', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_h2)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H2 header link problem') in errors

    def test_invalid_day_h3_only_one_day_in_thread(self, tmp_path):
        def invalidate_h2(day_text):
            return re.sub(r'(\n## .*?\n)', r'\1### ❮ X ❯ <wbr id=x>\n#### Y <wbr id=y>\n', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_h2)
        errors = logbook.parse().errors
        path = logbook.years[0].days[0].path
        assert ParseError(path, 'H3 header has id but no links') in errors
        assert ParseError(path, 'H4 header has id but no links') in errors

    def test_parse_invalid_day_footer_missing_rule(self, tmp_path):
        def remove_hr(day_text):
            return re.sub(r'<footer.*?footer>', '<footer></footer>', day_text)

        logbook = create_logbook_from_files(tmp_path, remove_hr)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_multiple_rules(self, tmp_path):
        def duplicate_hr(day_text):
            return re.sub(r'(<hr[^>]*?>)', r'\1\1', day_text)

        logbook = create_logbook_from_files(tmp_path, duplicate_hr)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_missing_stylesheet_link(self, tmp_path):
        def remove_link(day_text):
            return re.sub(r'<link[^>]*?>', '', day_text)

        logbook = create_logbook_from_files(tmp_path, remove_link)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_has_link_rel_different_than_stylesheet(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'rel=stylesheet', 'rel=prefetch', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_wrong_link_href(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'href=../../../style.css', 'href=style.css', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_missing_link_href(self, tmp_path):
        def invalidate_link(day_text):
            return re.sub(r'href=../../../style.css', '', day_text)

        logbook = create_logbook_from_files(tmp_path, invalidate_link)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_has_multiple_links(self, tmp_path):
        def duplicate_link(day_text):
            return re.sub(r'(<link[^>]*?>)', r'\1\1', day_text)

        logbook = create_logbook_from_files(tmp_path, duplicate_link)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer content problem') in footer.parse().errors

    def test_parse_invalid_day_footer_is_not_last_element(self, tmp_path):
        def add_content(day_text):
            return re.sub(r'(<footer.*?footer>)', r'\1<p>Finis</p>', day_text)

        logbook = create_logbook_from_files(tmp_path, add_content)
        footer = Footer(Day(logbook.root, DATE_1))
        assert ParseError(footer.path, 'Footer is not last element') in footer.parse().errors


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
        year1 = Year(Day(tmp_path, datetime.date(2020, 1, 1)))
        year2 = Year(Day(tmp_path, datetime.date(2021, 1, 1)))
        assert year1.path == tmp_path / '2020' / '2020.md'
        assert year2.path == tmp_path / '2021' / '2021.md'


class TestMonth:
    def test_dataclass(self, tmp_path):
        month1 = Month(Day(tmp_path, DATE_2))
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

    def test_path(self, tmp_path):
        day = Day(tmp_path, DATE_1)
        assert day.path == tmp_path / DAY_1_RELATIVE_PATH


class TestDayHeader:
    def test_dataclass(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        header1 = DayHeader(Day(logbook.root, DATE_2), 1)
        assert header1 == DayHeader(Day(logbook.root, DATE_2), 1)

    def test_template(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        day = Day(logbook.root, DATE_1)
        day.next[''] = Day(logbook.root, DATE_2)
        header = DayHeader(day, 1)
        assert header.template == '# ❮ [2020-08-20](../../2020.md#august) [❯](../../../2021/08/20/20210820.md)'


class TestMonthHeader:
    def test_template_only_month(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        month = Month(Day(logbook.root, DATE_1))
        assert not month.parse().errors
        th = MarkdownParser.markdown_to_html_fragment(month.header.template)
        assert th.text_content() == '❮ 2020-08 ❯'
        assert th.attrib['colspan'] == '7'
        a = next(th.iter('a'), None)
        assert a is not None
        assert a.text_content() == '2020-08'
        assert a.attrib['href'] == '../2020.md#august'

    def test_template_middle_month(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        month = Month(Day(logbook.root, DATE_2))
        month.previous = Month(Day(logbook.root, DATE_1))
        month.next = Month(Day(logbook.root, DATE_3))
        assert not month.parse().errors
        th = MarkdownParser.markdown_to_html_fragment(month.header.template)
        assert th.text_content() == '❮ 2021-08 ❯'
        assert th.attrib['colspan'] == '7'
        a = list(th.iter('a'))
        assert len(a) == 3
        assert a[0].text_content() == '❮'
        assert a[0].attrib['href'] == '../../2020/08/202008.md'
        assert a[1].text_content() == '2021-08'
        assert a[1].attrib['href'] == '../2021.md#august'
        assert a[2].text_content() == '❯'
        assert a[2].attrib['href'] == '../09/202109.md'


class TestYearHeader:
    def test_template_only_year(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        year = Year(Day(logbook.root, DATE_1))
        assert not year.parse().errors
        th = MarkdownParser.markdown_to_html_fragment(year.header.template)
        assert th.text_content() == '❮ 2020 ❯'
        assert th.attrib['colspan'] == '3'
        assert len(links := th.findall('.//a')) == 1
        assert links[0].text == '2020'
        assert links[0].attrib['href'] == '../index.md'

    def test_template_middle_year(self, tmp_path):
        logbook = create_logbook_from_files(tmp_path)
        year = Year(Day(logbook.root, DATE_2))
        year.previous = Year(Day(logbook.root, DATE_1))
        year.next = Year(Day(logbook.root, datetime.date(2022, 1, 1)))
        assert not year.parse().errors
        th = MarkdownParser.markdown_to_html_fragment(year.header.template)
        assert th.text_content() == '❮ 2021 ❯'
        assert th.attrib['colspan'] == '3'
        assert len(links := th.findall('.//a')) == 3
        assert links[0].text == '❮'
        assert links[0].attrib['href'] == '../2020/2020.md'
        assert links[1].text == '2021'
        assert links[1].attrib['href'] == '../index.md'
        assert links[2].text == '❯'
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


def test_lxml_471_emoji_bug():
    def assert_emoji_parsing(transform):
        # Woman Facepalming Emoji
        # See https://unicode.org/emoji/charts/full-emoji-list.html
        content = '<p>\U0001F926\u200D\u2640\uFE0F</p>'
        doc = document_fromstring(transform(content))
        assert doc[0][0].text == '\U0001F926\u200D\u2640\uFE0F'

    assert_emoji_parsing(lambda c: c)
    with pytest.raises(Exception):
        assert_emoji_parsing(lambda c: c.encode('utf-8'))
    assert_emoji_parsing(lambda c: c.encode('utf-16'))
    assert_emoji_parsing(lambda c: c.encode('utf-32'))


def create_logbook_from_files(root: Path, day_mutator: Callable[[str], str] = lambda s: s):
    logbook_path = root / 'logbook'
    shutil.copytree(TEST_ROOT / 'resources', logbook_path)
    day_path = logbook_path / DAY_1_RELATIVE_PATH
    day_path.write_text(day_mutator(day_path.read_text(encoding='utf-8')), encoding='utf-8')
    return Logbook(logbook_path)


class TestMarkdownParser:
    def test_move_inline_links_to_link_references(self):
        self.assert_normalized_markdown(
            '''
                # [❮](../prev.md) [Header](../top.md "Top") [❯](../next.md)
                
                paragraph
            ''',
            '''
                # [❮][1] [Header][2] [❯][3]
                
                paragraph
        
                [1]: ../prev.md
                [2]: ../top.md "Top"
                [3]: ../next.md
            ''')

    def test_detect_duplicates(self):
        self.assert_normalized_markdown(
            '''
                # [❮](linked.md) [Header](../top.md "Top") [❯](linked.md)
        
                paragraph
            ''',
            '''
                # [❮][1] [Header][2] [❯][1]
        
                paragraph
        
                [1]: linked.md
                [2]: ../top.md "Top"
            ''')

    def test_zero_fill_link_reference_labels(self):
        self.assert_normalized_markdown(
            '''
                # [A](a) [B](b) [C](c) [D](d) [E](e) [F](f) [G](g) [H](h) [I](i) [J](j)
        
                paragraph
            ''',
            '''
                # [A][01] [B][02] [C][03] [D][04] [E][05] [F][06] [G][07] [H][08] [I][09] [J][10]
        
                paragraph
        
                [01]: a
                [02]: b
                [03]: c
                [04]: d
                [05]: e
                [06]: f
                [07]: g
                [08]: h
                [09]: i
                [10]: j
            ''')

    def test_rearrange_existing_link_reference_definitions(self):
        self.assert_normalized_markdown(
            '''
                # [A](a) [B][1] [C](c) [D](c)
        
                paragraph
                
                [1]: b
            ''',
            '''
                # [A][1] [B][2] [C][3] [D][3]
        
                paragraph
        
                [1]: a
                [2]: b
                [3]: c
            ''')

    def test_image_links(self):
        self.assert_normalized_markdown(
            '''
                ![Alt](image.jpg "title")
            ''',
            '''
                ![Alt][1]
        
                [1]: image.jpg "title"
            ''')

    def test_autolink_does_not_create_link_reference_definition(self):
        self.assert_normalized_markdown(
            '''
                ## Test
                
                > Test <email@example.com>
                >
                > ![test](image.jpg)
                >
            ''',
            '''
                ## Test
                
                > Test <email@example.com>
                >
                > ![test][1]
                
                [1]: image.jpg
            ''')

    def test_auto_links_are_skipped(self):
        self.assert_normalized_markdown(
            '''
                Go to <https://www.google.com>
            ''',
            '''
                Go to <https://www.google.com>
            ''')

    def test_number_nested_links_depth_first(self):
        self.assert_normalized_markdown(
            '''
                [![Alt](image.jpg "title")](external.md) [Figure 1](list_of_figures.md)
            ''',
            '''
                [![Alt][1]][2] [Figure 1][3]
                
                [1]: image.jpg "title"
                [2]: external.md
                [3]: list_of_figures.md
            ''')

    def test_do_not_linkify(self):
        self.assert_normalized_markdown(
            '''
                - List all available workflows (Workpace.ID = 1)
            ''',
            '''
                - List all available workflows (Workpace.ID = 1)
            ''')

    @staticmethod
    def assert_normalized_markdown(input_markdown: str, expected_markdown: str):
        assert MarkdownParser.normalize_markdown(dedent(input_markdown).lstrip()) == dedent(expected_markdown).lstrip()
