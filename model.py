import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field, InitVar
from functools import cached_property, lru_cache
from pathlib import Path
from typing import List, TypeVar

from lxml import html
from lxml.html import HtmlElement
from markdown import markdown


@dataclass(frozen=True, order=True)
class ParseError:
    path: Path
    message: str


@dataclass(frozen=True)
class ParseResult:
    errors: List[ParseError] = field(default_factory=lambda: [])

    @property
    def valid(self) -> bool:
        return not self.errors

    def add_error(self, path: Path, message: str) -> 'ParseResult':
        self.errors.append(ParseError(path, message))
        return self


class Parsable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def path(self) -> Path:
        pass

    def parse(self) -> ParseResult:
        return self.Parser(self).parse()

    @dataclass
    class Parser(metaclass=ABCMeta):
        context: 'ExtendsParsable'
        result: ParseResult = ParseResult()

        @abstractmethod
        def parse(self) -> ParseResult:
            pass


ExtendsParsable = TypeVar('ExtendsParsable', bound=Parsable)


@dataclass(frozen=True, order=True)
class Logbook(Parsable):
    root: Path

    @cached_property
    def path(self) -> Path:
        return self.root

    @cached_property
    def years(self) -> List['Year']:
        return [Year(self.root, datetime.date(2021, 1, 1))]

    class Parser(Parsable.Parser):
        def parse(self) -> ParseResult:
            return self.result


@dataclass(frozen=True, order=True)
class Year(Parsable):
    root: Path
    year: int = field(init=False)
    date: InitVar[datetime.date]

    def __post_init__(self, date: datetime.date):
        object.__setattr__(self, 'year', date.year)

    @cached_property
    def path(self) -> Path:
        yyyy = f'{self.year:04d}'
        return self.root / yyyy / f'{yyyy}.md'

    @cached_property
    def months(self) -> List['Month']:
        return [Month(self.root, datetime.date(2021, 8, 1)), Month(self.root, datetime.date(2021, 9, 1))]

    @cached_property
    def days(self) -> List['Day']:
        return [Day(self.root, datetime.date(2021, 8, 20)), Day(self.root, datetime.date(2021, 9, 19))]

    class Parser(Parsable.Parser):
        def parse(self) -> ParseResult:
            return self.result


@dataclass(frozen=True, order=True)
class Month(Parsable):
    root: Path
    year: int = field(init=False)
    month: int = field(init=False)
    date: InitVar[datetime.date]

    def __post_init__(self, date: datetime.date):
        object.__setattr__(self, 'year', date.year)
        object.__setattr__(self, 'month', date.month)

    @cached_property
    def path(self) -> Path:
        yyyy, mm = f'{self.year:04d}', f'{self.month:02d}'
        return self.root / yyyy / mm / f'{yyyy}{mm}.md'

    @cached_property
    def days(self) -> List['Day']:
        return [Day(self.root, datetime.date(2021, 8, 20)), Day(self.root, datetime.date(2021, 9, 19))]

    class Parser(Parsable.Parser):
        def parse(self) -> ParseResult:
            return self.result


@dataclass(frozen=True, order=True)
class Day(Parsable):
    root: Path
    year: int = field(init=False)
    month: int = field(init=False)
    day: int = field(init=False)
    date: InitVar[datetime.date]

    def __post_init__(self, date: datetime.date):
        object.__setattr__(self, 'year', date.year)
        object.__setattr__(self, 'month', date.month)
        object.__setattr__(self, 'day', date.day)

    @cached_property
    def path(self) -> Path:
        yyyy, mm, dd = f'{self.year:04d}', f'{self.month:02d}', f'{self.day:02d}'
        return self.root / yyyy / mm / dd / f'{yyyy}{mm}{dd}.md'

    class Parser(Parsable.Parser):
        def parse(self) -> ParseResult:
            if not self.context.path.exists():
                self.result.add_error(self.context.path, 'Markdown file does not exist')
                return self.result
            tree = parse_markdown(self.context.path)
            if len(tree) > 0 and tree[-1].tag != 'footer':
                self.result.add_error(self.context.path, 'Missing footer')
            return self.result


@lru_cache
def parse_markdown(path: Path) -> HtmlElement:
    return html.fragment_fromstring(
        markdown(path.read_text(encoding='utf-8'),
                 output_format='html',
                 extensions=['markdown.extensions.extra']),
        create_parent=True)
