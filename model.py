import datetime
import re
from abc import ABCMeta, abstractmethod
from calendar import month_name, HTMLCalendar
from dataclasses import dataclass, field, InitVar
from functools import cached_property, lru_cache
from itertools import pairwise
from os import walk
from os.path import relpath
from pathlib import Path
from typing import List, TypeVar, Generic, final, Pattern, ClassVar, Union, Optional

from lxml import html
from lxml.builder import E
from lxml.html import HtmlElement, document_fromstring
from markdown import markdown


def _late_init_field():
    return field(compare=False, init=False, default=None, hash=False, repr=False)


def _late_init_list():
    return field(compare=False, init=False, default_factory=lambda: [], hash=False, repr=False)


@dataclass(frozen=True, order=True)
class ParseError:
    path: Path
    message: str
    hint: str = field(default=None, compare=False)

    def __repr__(self) -> str:
        return f'ParseError(path={repr(self.path.name)}, message={repr(self.message)})'


@dataclass(frozen=True)
class ParseResult:
    errors: List[ParseError] = field(default_factory=lambda: [])

    @property
    def valid(self) -> bool:
        return not self.errors

    def add_error(self, path: Path, message: str, hint: str = None) -> 'ParseResult':
        self.errors.append(ParseError(path, message, hint))
        return self

    def reset(self):
        self.errors.clear()
        return self

    def update(self, other: 'ParseResult'):
        self.errors.extend(other.errors)
        return self


ExtendsParsable = TypeVar('ExtendsParsable', bound='Parsable')


class Parsable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def path(self) -> Path:
        pass

    @property
    @abstractmethod
    def template(self) -> str:
        pass

    @final
    def parse(self) -> ParseResult:
        return self.Parser(self).parse()

    @final
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.path.write_text(self.template, encoding='utf-8')

    @dataclass
    class Parser(Generic[ExtendsParsable], metaclass=ABCMeta):
        context: ExtendsParsable
        result: ParseResult = field(init=False)

        @final
        def __post_init__(self):
            self.result = ParseResult().add_error(self.context.path, 'Not parsed')

        @abstractmethod
        def parse(self) -> ParseResult:
            pass


@dataclass(unsafe_hash=True, order=True)
class Day(Parsable):
    root: Path = field(hash=True, repr=False)
    year: int = field(init=False, hash=True)
    month: int = field(init=False, hash=True)
    day: int = field(init=False, hash=True)
    date: InitVar[datetime.date]

    previous: Optional['Day'] = _late_init_field()
    next: Optional['Day'] = _late_init_field()

    headers: Optional['DayHeader'] = _late_init_list()
    ids: Optional['str'] = _late_init_list()
    footer: Optional['Footer'] = _late_init_field()

    PATH_PATTERN: ClassVar[Pattern] = re.compile(r'^(?P<yyyy>[0-9]{4}).'
                                                 r'(?P<mm>[0-9]{2}).'
                                                 r'(?P<dd>[0-9]{2}).'
                                                 r'(?P<md>(?P=yyyy)(?P=mm)(?P=dd)\.md)$')

    def __post_init__(self, date: datetime.date):
        self.year = date.year
        self.month = date.month
        self.day = date.day

    @cached_property
    def path(self) -> Path:
        yyyy, mm, dd = f'{self.year:04d}', f'{self.month:02d}', f'{self.day:02d}'
        return self.root / yyyy / mm / dd / f'{yyyy}{mm}{dd}.md'

    @cached_property
    def template(self) -> str:
        return '\n'.join([
            DayHeader(self, 1).template,
            '',
            Footer(self).template,
            ''
        ])

    @staticmethod
    def create(root: Path) -> List['Day']:
        def day(path: Path):
            return Day(root, datetime.date(int(path.name[0:4]), int(path.name[4:6]), int(path.name[6:8])))

        def pattern_matches(path: Path):
            return Day.PATH_PATTERN.match(relative_path(path, root))

        days = list(map(day, filter(pattern_matches, sorted(root.rglob('*.md')))))

        for prv, cur in pairwise(days):
            prv.next = cur
            cur.previous = prv

        return days

    class Parser(Parsable.Parser['Day']):
        @cached_property
        def doc(self):
            return parse_markdown(self.context.path)

        def parse(self) -> ParseResult:
            self.result.reset()
            if not self.context.path.exists():
                return self.result.add_error(self.context.path, 'Markdown file does not exist')
            self.__parse_headers()
            self.__parse_ids()
            self.__parse_footer()
            return self.result

        def __parse_headers(self):
            self.context.headers = [DayHeader(self.context,
                                              int(h.tag[1]),
                                              self.doc.getroottree().getpath(h))
                                    for h in self.doc.xpath(DayHeader.H1_XPATH)]
            if not (h1s := [h for h in self.context.headers if h.level == 1]):
                self.result.add_error(self.context.path, 'Missing H1 header', DayHeader(self.context, 1).template)
            elif len(h1s) > 1:
                self.result.add_error(self.context.path, 'Multiple H1 headers', DayHeader(self.context, 1).template)
            for h in self.context.headers:
                self.result.update(h.parse())

        def __parse_ids(self):
            self.context.ids = [str(i) for i in self.doc.xpath('//*[@id]/@id')]

        def __parse_footer(self):
            if not (footers := [Footer(self.context) for _ in self.doc.xpath(Footer.XPATH)]):
                self.result.add_error(self.context.path, 'Missing footer', Footer(self.context).template)
            elif len(footers) > 1:
                self.result.add_error(self.context.path, 'Multiple footers')
            else:
                self.context.footer = footers[0]
                self.result.update(self.context.footer.parse())


@dataclass(unsafe_hash=True, order=True)
class Month(Parsable):
    root: Path = field(init=False, hash=True, repr=False)
    year: int = field(init=False, hash=True)
    month: int = field(init=False, hash=True)
    day: InitVar[Day]

    previous: Optional['Month'] = _late_init_field()
    next: Optional['Month'] = _late_init_field()

    days: List[Day] = _late_init_list()

    def __post_init__(self, day: Day):
        self.root = day.root
        self.year = day.year
        self.month = day.month

    @cached_property
    def path(self) -> Path:
        yyyy, mm = f'{self.year:04d}', f'{self.month:02d}'
        return self.root / yyyy / mm / f'{yyyy}{mm}.md'

    @cached_property
    def name(self) -> str:
        return month_name[self.month].lower()

    @cached_property
    def header(self) -> 'MonthHeader':
        return MonthHeader(self)

    @cached_property
    def footer(self) -> 'Footer':
        return Footer(self)

    @cached_property
    def template(self) -> str:
        table = html.fragment_fromstring(HTMLCalendar().formatmonth(self.year, self.month))
        table.attrib.pop('border', None)
        table.attrib.pop('cellpadding', None)
        table.attrib.pop('cellspacing', None)
        for e in table.iter('th', 'td'):
            e.attrib.pop('class', None)
        month_header = parse_markdown_element(self.header.template)
        month_rows = table.iter('tr')
        month_header_row = next(month_rows, None)
        month_header_row.clear()
        month_header_row.append(month_header)
        week_headers = next(month_rows, [])
        for th in week_headers:
            th.text = th.text[0:2]
        days = {str(d.day): d for d in self.days}
        for day_cell in [td for td in table.iter('td') if td.text in days]:
            href = relative_path(days[day_cell.text].path, self.path.parent)
            day_link = E.a(day_cell.text, dict(href=href))
            day_cell.clear()
            day_cell.append(day_link)

        return '\n'.join([
            html_to_string(table),
            '',
            self.footer.template,
            ''
        ])

    @staticmethod
    def create(days: List[Day]) -> List['Month']:
        months = {}
        for d in days:
            month = months.setdefault((d.year, d.month), Month(d))
            month.days.append(d)
        month_list = sorted(months.values())
        for prv, cur in pairwise(month_list):
            prv.next = cur
            cur.previous = prv
        return month_list

    class Parser(Parsable.Parser['Month']):
        def parse(self) -> ParseResult:
            return self.result.reset()


@dataclass(unsafe_hash=True, order=True)
class Year(Parsable):
    root: Path = field(init=False, hash=True, compare=True, repr=False)
    year: int = field(init=False, hash=True, compare=True)
    day: InitVar[Day]

    previous: Optional['Year'] = _late_init_field()
    next: Optional['Year'] = _late_init_field()

    days: List[Day] = _late_init_list()
    months: List[Month] = _late_init_list()

    def __post_init__(self, day: Day):
        self.root = day.root
        self.year = day.year

    @cached_property
    def path(self) -> Path:
        yyyy = f'{self.year:04d}'
        return self.root / yyyy / f'{yyyy}.md'

    @cached_property
    def template(self) -> str:
        table = html.fragment_fromstring(HTMLCalendar().formatyear(self.year))
        for t in [table] + table.findall('.//table'):
            t.attrib.pop('border', None)
            t.attrib.pop('cellpadding', None)
            t.attrib.pop('cellspacing', None)
        for e in table.iter('th', 'td'):
            e.attrib.pop('class', None)
        months = {m.name: m for m in self.months}
        for month_table in table.findall('.//table'):
            rows = month_table.iter('tr')
            month_header_row = next(rows, None)
            month_header = next(month_header_row.iter('th'), HtmlElement())
            if (month_key := month_header.text.lower()) in months:
                month_href = relative_path(months[month_key].path, self.path.parent)
                month_link = E.a(month_header.text, dict(href=month_href))
                month_header.clear()
                month_header.attrib['colspan'] = '7'
                month_header.append(month_link)
                days = {str(d.day): d for d in months[month_key].days}
                for day_cell in [td for td in month_table.findall('.//td') if td.text in days]:
                    day_href = relative_path(days[day_cell.text].path, self.path.parent)
                    day_link = E.a(day_cell.text, dict(href=day_href))
                    day_cell.clear()
                    day_cell.append(day_link)
                    month_table.getparent().attrib['id'] = months[month_key].name
            week_headers = next(rows, [])
            for th in week_headers:
                th.text = th.text[0:2]

        year_header = parse_markdown_element(self.header.template)
        year_header_row = next(table.iter('tr'), None)
        year_header_row.clear()
        year_header_row.append(year_header)
        return '\n'.join([
            html_to_string(table),
            '',
            self.footer.template,
            ''
        ])

    @cached_property
    def header(self) -> 'YearHeader':
        return YearHeader(self)

    @cached_property
    def footer(self) -> 'Footer':
        return Footer(self)

    @staticmethod
    def create(days: List[Day]):
        years = {}
        for d in days:
            year = years.setdefault(d.year, Year(d))
            year.days.append(d)
        year_list = sorted(years.values())
        for prv, cur in pairwise(year_list):
            prv.next = cur
            cur.previous = prv
        return year_list

    class Parser(Parsable.Parser['Year']):
        def parse(self) -> ParseResult:
            self.result.reset()
            for m in self.context.months:
                self.result.update(m.parse())
            for d in self.context.days:
                self.result.update(d.parse())
            return self.result


@dataclass(order=True)
class Logbook(Parsable):
    root: Path

    years: List[Year] = _late_init_list()

    @cached_property
    def path(self) -> Path:
        return self.root / 'index.md'

    @cached_property
    def footer(self) -> 'Footer':
        return Footer(self)

    @cached_property
    def template(self) -> str:
        table = E.table({'class': 'year'})
        years = {y.year: y for y in self.years}
        year_range = list(range(10 * (self.years[0].year // 10), self.years[-1].year + 1))
        tr = E.tr()
        for y in year_range:
            if not y % 10:
                table.append(tr := E.tr())
            if y in years:
                tr.append(E.th(
                    E.a(str(y), dict(href=relative_path(years[y].path, self.path.parent)))
                ))
            else:
                tr.append(E.th(str(y)))
        return '\n'.join([
            html_to_string(table),
            '',
            self.footer.template,
            ''
        ])

    class Parser(Parsable.Parser['Logbook']):
        def parse(self) -> ParseResult:
            self.result.reset()
            self.__validate_constraints()
            self.__create_time_entities()
            self.__parse_dependencies()
            self.__save_time_entities()
            return self.result

        def __validate_constraints(self):
            if not (self.context.path.parent / 'style.css').exists():
                self.result.add_error(self.context.path.parent, 'Missing style.css')
            for root, dirs, files in walk(self.context.root):
                for d in dirs:
                    if d in {'.git', '.hg'}:
                        dirs.remove(d)
                        continue
                    if not next((dir_path := Path(root) / d).iterdir(), None):
                        self.result.add_error(dir_path, 'Empty directory')

        def __create_time_entities(self):
            days = Day.create(self.context.root)
            months = Month.create(days)
            self.context.years = Year.create(days)
            for y in self.context.years:
                y.months = [m for m in months if m.year == y.year]

        def __parse_dependencies(self):
            for y in self.context.years:
                self.result.update(y.parse())

        def __save_time_entities(self):
            if self.result.valid:
                self.context.save()
                for y in self.context.years:
                    y.save()
                    for m in y.months:
                        m.save()


@dataclass
class DayHeader(Parsable):
    day: Day
    level: int
    xpath: Optional[str] = None

    H1_XPATH: ClassVar[str] = '/html/body/h1'
    XPATH: ClassVar[str] = f'/html/body/*[{" or ".join(["self::h{}".format(i + 1) for i in range(6)])}]'

    @property
    def path(self) -> Path:
        return self.day.path

    @cached_property
    def template(self) -> str:
        if self.level == 1:
            return self.__h1_template()

    def __h1_template(self):
        def backward_href():
            return relative_path(self.day.previous.path, self.day.path.parent)

        def forward_href():
            return relative_path(self.day.next.path, self.day.path.parent)

        backward = '❮' if self.day.previous is None else f'[❮]({backward_href()})'
        forward = '❯' if self.day.next is None else f'[❯]({forward_href()})'
        yyyy = f'{self.day.year:04d}'
        up_text = f'{yyyy}-{self.day.month:02d}-{self.day.day:02d}'
        up_href = f'../../{yyyy}.md#{month_name[self.day.month].lower()}'
        upward = f'[{up_text}]({up_href})'
        return f'# {backward} {upward} {forward}'

    class Parser(Parsable.Parser['DayHeader']):
        @cached_property
        def doc(self) -> HtmlElement:
            return parse_markdown(self.context.path)

        def parse(self) -> ParseResult:
            self.result.reset()
            if self.context.level == 1:
                self.__parse_h1()
            return self.result

        def __parse_h1(self):
            actual = self.doc.xpath(self.context.xpath or DayHeader.H1_XPATH)[0]
            if actual.getprevious() is not None:
                self.result.add_error(self.context.path, 'H1 header is not first element')
            else:
                expected = parse_markdown_element(self.context.template)
                if html_to_string(expected) != html_to_string(actual):
                    self.result.add_error(self.context.path, 'H1 header content problem', self.context.template)


@dataclass
class MonthHeader:
    month: Month

    @property
    def template(self) -> str:
        def backward_href():
            return relative_path(self.month.previous.path, self.month.path.parent)

        def forward_href():
            return relative_path(self.month.next.path, self.month.path.parent)

        yyyy = f'{self.month.year:04d}'
        mm = f'{self.month.month:02d}'
        backward = f'<a href={backward_href()}>❮</a>' if self.month.previous else '❮'
        forward = f'<a href={forward_href()}>❯</a>' if self.month.next else '❯'
        upward = f'<a href=../{yyyy}.md#{self.month.name}>{yyyy}-{mm}</a>'
        return f'<th colspan=7>{backward} {upward} {forward}</th>'


@dataclass
class YearHeader:
    year: Year

    @property
    def template(self) -> str:
        def backward_href():
            return relative_path(self.year.previous.path, self.year.path.parent)

        def forward_href():
            return relative_path(self.year.next.path, self.year.path.parent)

        yyyy = f'{self.year.year:04d}'
        backward = f'<a href={backward_href()}>❮</a>' if self.year.previous else '❮'
        forward = f'<a href={forward_href()}>❯</a>' if self.year.next else '❯'
        upward = f'<a href=../index.md>{yyyy}</a>'
        return f'<th colspan=3>{backward} {upward} {forward}</th>'


@dataclass(order=True)
class Footer(Parsable):
    container: Union[Logbook, Year, Month, Day]

    XPATH: ClassVar[str] = '/html/body/footer'

    @cached_property
    def path(self) -> Path:
        return self.container.path

    @cached_property
    def template(self) -> str:
        style_href = relative_path(self.container.root / 'style.css', self.path.parent)
        return f'<footer><link href={style_href} rel=stylesheet><hr></footer>'

    class Parser(Parsable.Parser['Footer']):

        @cached_property
        def doc(self):
            return parse_markdown(self.context.path)

        def parse(self) -> ParseResult:
            self.result.reset()
            footer = self.doc.xpath(self.context.XPATH)[0]
            if footer.getnext() is not None:
                self.result.add_error(self.context.path, 'Footer is not last element')
            elif html_to_string(parse_markdown_element(self.context.template)) != html_to_string(footer):
                self.result.add_error(self.context.path, 'Footer content problem', self.context.template)
            return self.result


@lru_cache
def parse_markdown(path: Path) -> HtmlElement:
    content = markdown(path.read_text(encoding='utf-8'), output_format='html',
                       extensions=['extra']).strip()
    return document_fromstring(content)


def parse_markdown_element(string: str) -> HtmlElement:
    return html.fragment_fromstring(
        markdown(string,
                 output_format='html',
                 extensions=['extra']).strip())


def html_to_string(element: HtmlElement) -> str:
    return html.tostring(element, encoding='unicode', pretty_print=True).strip()


def relative_path(path: Path, start: Path):
    return Path(relpath(path, start)).as_posix()


def invalidate_cache():
    parse_markdown.cache_clear()
