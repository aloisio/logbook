import datetime
import re
from abc import ABCMeta, abstractmethod
from calendar import month_name
from dataclasses import dataclass, field, InitVar
from functools import cached_property, lru_cache
from itertools import pairwise
from os.path import relpath
from pathlib import Path
from typing import List, TypeVar, Generic, final, Pattern, ClassVar, Union, Iterable, Any, Dict, \
    Optional

from lxml import html
from lxml.html import HtmlElement
from lxml.html.soupparser import fromstring
from markdown import markdown


@dataclass(frozen=True, order=True)
class ParseError:
    path: Path
    message: str
    hint: str = field(default=None, compare=False)


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


@dataclass(order=True)
class Day(Parsable):
    root: Path
    year: int = field(init=False)
    month: int = field(init=False)
    day: int = field(init=False)
    date: InitVar[datetime.date]
    previous: 'Day' = field(compare=False, init=False, default=None)
    next: 'Day' = field(compare=False, init=False, default=None)

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

    @staticmethod
    @lru_cache
    def create(root: Path) -> List['Day']:
        def date(path: Path):
            return datetime.date(int(path.name[0:4]), int(path.name[4:6]), int(path.name[6:8]))

        dates = list(map(date, filter(lambda p: Day.PATH_PATTERN.match(p.as_posix()), sorted(root.rglob('*.md')))))
        dates.insert(0, None)
        dates.append(None)

        days_per_date: Dict[Optional[datetime.date], Optional[Day]] = {None: None}

        for prv, cur, nxt in triplewise(dates):
            days_per_date.setdefault(prv, Day(root, prv) if prv else None)
            days_per_date.setdefault(cur, Day(root, cur))
            days_per_date.setdefault(nxt, Day(root, nxt) if nxt else None)
            days_per_date[cur].previous = days_per_date[prv]
            days_per_date[cur].next = days_per_date[nxt]

        return list(map(days_per_date.get, filter(None, dates)))

    class Parser(Parsable.Parser['Day']):
        def parse(self) -> ParseResult:
            self.result.reset()
            if not self.context.path.exists():
                return self.result.add_error(self.context.path, 'Markdown file does not exist')
            self.result.update(DayHeader(self.context).parse())
            return self.result.update(Footer(self.context).parse())


@dataclass(frozen=True, order=True)
class Year(Parsable):
    root: Path = field(init=False)
    year: int = field(init=False)
    day: InitVar[Day]

    def __post_init__(self, day: Day):
        object.__setattr__(self, 'root', day.root)
        object.__setattr__(self, 'year', day.year)

    @cached_property
    def path(self) -> Path:
        yyyy = f'{self.year:04d}'
        return self.root / yyyy / f'{yyyy}.md'

    @cached_property
    def months(self) -> List['Month']:
        return sorted({Month(d) for d in self.days})

    @cached_property
    def days(self) -> List['Day']:
        return [d for d in Day.create(self.root) if d.year == self.year]

    class Parser(Parsable.Parser['Year']):
        def parse(self) -> ParseResult:
            return self.result.reset()


@dataclass(frozen=True, order=True)
class Month(Parsable):
    root: Path = field(init=False)
    year: int = field(init=False)
    month: int = field(init=False)
    day: InitVar[Day]

    def __post_init__(self, day: Day):
        object.__setattr__(self, 'root', day.root)
        object.__setattr__(self, 'year', day.year)
        object.__setattr__(self, 'month', day.month)

    @cached_property
    def path(self) -> Path:
        yyyy, mm = f'{self.year:04d}', f'{self.month:02d}'
        return self.root / yyyy / mm / f'{yyyy}{mm}.md'

    @cached_property
    def name(self) -> str:
        return month_name[self.month].lower()

    @cached_property
    def days(self) -> List['Day']:
        return [d for d in Day.create(self.root) if d.month == self.month]

    class Parser(Parsable.Parser['Month']):
        def parse(self) -> ParseResult:
            return self.result.reset()


@dataclass(order=True)
class Logbook(Parsable):
    root: Path

    @cached_property
    def path(self) -> Path:
        return self.root / 'index.md'

    @cached_property
    def years(self) -> List[Year]:
        return sorted({Year(d) for d in Day.create(self.root)})

    class Parser(Parsable.Parser['Logbook']):
        def parse(self) -> ParseResult:
            return self.result.reset()


@dataclass(frozen=True, order=True)
class InternalLink:
    source: Path
    destination: Path
    fragment: str = None


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
    return html.tostring(element, encoding='unicode').strip()


def triplewise(iterable: Iterable[Any]):
    """Return overlapping triplets from an iterable"""
    # triplewise('ABCDEFG') -> ABC BCD CDE DEF EFG
    for (a, _), (b, c) in pairwise(pairwise(iterable)):
        yield a, b, c
