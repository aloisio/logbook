import datetime
import re
from abc import ABCMeta, abstractmethod
from calendar import month_name, HTMLCalendar
from dataclasses import dataclass, field, InitVar
from functools import cached_property, lru_cache
from itertools import pairwise, islice
from os.path import relpath
from pathlib import Path
from typing import List, TypeVar, Generic, final, Pattern, ClassVar, Union

from lxml import html
from lxml.html import HtmlElement
from lxml.html.soupparser import fromstring
from markdown import markdown


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

    @final
    def parse(self) -> ParseResult:
        return self.Parser(self).parse()

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
    previous: 'Day' = field(compare=False, init=False, default=None, hash=False, repr=False)
    next: 'Day' = field(compare=False, init=False, default=None, hash=False, repr=False)

    PATH_PATTERN: ClassVar[Pattern] = re.compile(r'^.*?(?P<yyyy>[0-9]{4}).'
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
    def headers(self):
        return [DayHeader(self)]

    @staticmethod
    @lru_cache
    def create(root: Path) -> List['Day']:
        def day(path: Path):
            return Day(root, datetime.date(int(path.name[0:4]), int(path.name[4:6]), int(path.name[6:8])))

        days = list(map(day, filter(lambda p: Day.PATH_PATTERN.match(p.as_posix()), sorted(root.rglob('*.md')))))

        for prv, cur in pairwise(days):
            prv.next = cur
            cur.previous = prv

        return days

    class Parser(Parsable.Parser['Day']):
        def parse(self) -> ParseResult:
            self.result.reset()
            if not self.context.path.exists():
                return self.result.add_error(self.context.path, 'Markdown file does not exist')
            return self.result.update(Footer(self.context).parse())


@dataclass(unsafe_hash=True, order=True)
class Year(Parsable):
    root: Path = field(init=False, hash=True, compare=True, repr=False)
    year: int = field(init=False, hash=True, compare=True)
    day: InitVar[Day]
    previous: 'Year' = field(compare=False, init=False, hash=False, default=None, repr=False)
    next: 'Year' = field(compare=False, init=False, hash=False, default=None, repr=False)

    def __post_init__(self, day: Day):
        self.root = day.root
        self.year = day.year

    @cached_property
    def path(self) -> Path:
        yyyy = f'{self.year:04d}'
        return self.root / yyyy / f'{yyyy}.md'

    @cached_property
    def months(self) -> List['Month']:
        return [m for m in Month.create(self.root) if m.year == self.year]

    @cached_property
    def days(self) -> List['Day']:
        return [d for d in Day.create(self.root) if d.year == self.year]

    @cached_property
    def footer(self) -> 'Footer':
        return Footer(self)

    @staticmethod
    def create(root: Path):
        years = sorted({Year(d) for d in Day.create(root)})
        for prv, cur in pairwise(years):
            prv.next = cur
            cur.previous = prv
        return years

    class Parser(Parsable.Parser['Year']):
        def parse(self) -> ParseResult:
            self.result.reset()
            for m in self.context.months:
                self.result.update(m.parse())
            for d in self.context.days:
                self.result.update(d.parse())
                for h in d.headers:
                    self.result.update(h.parse())
            if self.result.valid:
                self.context.path.touch(exist_ok=True)
                self.context.path.write_text(self.context.footer.template)

            return self.result


@dataclass(unsafe_hash=True, order=True)
class Month(Parsable):
    root: Path = field(init=False, hash=True, repr=False)
    year: int = field(init=False, hash=True)
    month: int = field(init=False, hash=True)
    day: InitVar[Day]
    previous: 'Month' = field(compare=False, init=False, hash=False, default=None, repr=False)
    next: 'Month' = field(compare=False, init=False, hash=False, default=None, repr=False)

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
    def days(self) -> List['Day']:
        return [d for d in Day.create(self.root) if d.year == self.year and d.month == self.month]

    @cached_property
    def template(self) -> str:
        table = html.fragment_fromstring(HTMLCalendar().formatmonth(self.year, self.month))
        table.attrib.pop('border', None)
        table.attrib.pop('cellpadding', None)
        table.attrib.pop('cellspacing', None)
        for e in table.iter('th', 'td'):
            e.attrib.pop('class', None)
        month_header = parse_markdown_element(self.header.template)
        month_header_row = next(table.iter('tr'), None)
        month_header_row.clear()
        month_header_row.append(month_header)
        week_headers = next(islice(table.iter('tr'), 1, None), [])
        for th in week_headers:
            th.text = th.text[0:2]
        return '\n'.join([
            html_to_string(table),
            self.footer.template,
            ''
        ])

    @staticmethod
    def create(root: Path) -> List['Month']:
        months = sorted({Month(d) for d in Day.create(root)})
        for prv, cur in pairwise(months):
            prv.next = cur
            cur.previous = prv
        return months

    class Parser(Parsable.Parser['Month']):
        def parse(self) -> ParseResult:
            self.result.reset()
            self.context.path.touch(exist_ok=True)
            self.context.path.write_text(self.context.template)
            return self.result


@dataclass(order=True)
class Logbook(Parsable):
    root: Path

    @cached_property
    def path(self) -> Path:
        return self.root / 'index.md'

    @cached_property
    def years(self) -> List[Year]:
        return sorted({Year(d) for d in Day.create(self.root)})

    @cached_property
    def footer(self) -> 'Footer':
        return Footer(self)

    class Parser(Parsable.Parser['Logbook']):
        def parse(self) -> ParseResult:
            self.result.reset()
            if not (self.context.path.parent / 'style.css').exists():
                self.result.add_error(self.context.path.parent, 'Missing style.css')
            for y in self.context.years:
                self.result.update(y.parse())
            if self.result.valid:
                self.context.path.touch(exist_ok=True)
                self.context.path.write_text(self.context.footer.template)
            return self.result


@dataclass(order=True)
class DayHeader(Parsable):
    day: Day

    @property
    def path(self) -> Path:
        return self.day.path

    @cached_property
    def template(self) -> str:
        backward = '◀' if self.day.previous is None else f'[◀]({relpath(self.day.previous.path, self.day.path.parent)})'
        forward = '▶' if self.day.next is None else f'[▶]({relpath(self.day.next.path, self.day.path.parent)})'
        up_text = f'{self.day.year:04d}-{self.day.month:02d}-{self.day.day:02d}'
        upward = f'[{up_text}]({relpath(Year(self.day).path, self.day.path.parent)}#{Month(self.day).name})'
        return f'# {backward} {upward} {forward}'

    class Parser(Parsable.Parser['DayHeader']):
        def parse(self) -> ParseResult:
            self.result.reset()
            tree = parse_markdown(self.context.path)
            if not (h1s := tree.findall('./h1')):
                return self.result.add_error(self.context.path, 'Missing header', self.context.template)
            if len(h1s) > 1:
                self.result.add_error(self.context.path, 'Multiple headers')
            if h1s[0].getprevious() is not None:
                self.result.add_error(self.context.path, 'Header is not first element')
            expected = parse_markdown_element(self.context.template)
            if html_to_string(expected) != html_to_string(h1s[0]):
                self.result.add_error(self.context.path, 'Header content problem', self.context.template)
            return self.result


@dataclass
class MonthHeader():
    month: Month

    @property
    def template(self) -> str:
        yyyy = f'{self.month.year:04d}'
        mm = f'{self.month.month:02d}'
        backward = f'<a href={relpath(self.month.previous.path, self.month.path.parent)}>◀</a>' if self.month.previous else '◀'
        forward = f'<a href={relpath(self.month.next.path, self.month.path.parent)}>▶</a>' if self.month.next else '▶'
        upward = f'<a href=../{yyyy}.md#{self.month.name}>{yyyy}-{mm}</a>'
        return f'<th colspan=7>{backward} {upward} {forward}</th>'


@dataclass(order=True)
class Footer(Parsable):
    container: Union[Logbook, Year, Month, Day]

    @cached_property
    def path(self) -> Path:
        return self.container.path

    @cached_property
    def template(self) -> str:
        style_href = relpath(self.container.root / 'style.css', self.path.parent)
        return f'<footer><link href={style_href} rel=stylesheet><hr></footer>'

    class Parser(Parsable.Parser['Footer']):
        @cached_property
        def tree(self):
            return parse_markdown(self.context.path)

        def parse(self) -> ParseResult:
            self.result.reset()
            if not (footers := self.tree.findall('.//footer')):
                self.result.add_error(self.context.path, 'Missing footer', self.context.template)
            elif len(footers) > 1:
                self.result.add_error(self.context.path, 'Multiple footers')
            elif footers[0].getnext() is not None:
                self.result.add_error(self.context.path, 'Footer is not last element')
            elif html_to_string(parse_markdown_element(self.context.template)) != html_to_string(footers[0]):
                self.result.add_error(self.context.path, 'Footer content problem', self.context.template)
            return self.result


@lru_cache
def parse_markdown(path: Path) -> HtmlElement:
    # Using slower beautifulsoup parser because lxml mangles input with emojis
    return fromstring(
        markdown(path.read_text(encoding='utf-8'), output_format='html').strip())


def parse_markdown_element(string: str) -> HtmlElement:
    return html.fragment_fromstring(markdown(string, output_format='html'))


def html_to_string(element: HtmlElement) -> str:
    return html.tostring(element, encoding='unicode', pretty_print=True).strip()
