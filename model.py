import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field, InitVar
from functools import cached_property, lru_cache
from os.path import relpath
from pathlib import Path
from textwrap import dedent
from typing import List, TypeVar, Generic, final

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


@dataclass(frozen=True, order=True)
class Logbook(Parsable):
    root: Path

    @cached_property
    def path(self) -> Path:
        return self.root / 'index.md'

    @cached_property
    def years(self) -> List['Year']:
        return [Year(self.root, datetime.date(2021, 1, 1))]

    class Parser(Parsable.Parser['Logbook']):
        def parse(self) -> ParseResult:
            return self.result.reset()


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

    class Parser(Parsable.Parser['Year']):
        def parse(self) -> ParseResult:
            return self.result.reset()


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

    class Parser(Parsable.Parser['Month']):
        def parse(self) -> ParseResult:
            return self.result.reset()


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

    @cached_property
    def footer(self):
        return Footer(self.root, self.path)

    class Parser(Parsable.Parser['Day']):
        def parse(self) -> ParseResult:
            self.result.reset()
            if not self.context.path.exists():
                return self.result.add_error(self.context.path, 'Markdown file does not exist')
            return self.result.update(self.context.footer.parse())


@dataclass(frozen=True, order=True)
class InternalLink:
    source: Path
    destination: Path
    fragment: str = None


@dataclass(order=True)
class Footer(Parsable):
    root: Path
    path: Path
    link: InternalLink = None

    @cached_property
    def path(self) -> Path:
        return self.path

    @cached_property
    def template(self) -> str:
        style_href = relpath(self.root / 'style.css', self.path.parent)
        return dedent(f'''
            <footer><link href={style_href} rel=stylesheet><hr></footer>
        ''')

    class Parser(Parsable.Parser['Footer']):
        @cached_property
        def tree(self):
            return parse_markdown(self.context.path)

        def parse(self) -> ParseResult:
            self.result.reset()
            if (footer := self.__parse_footer_element()) is not None:
                self.__parse_horizontal_rule(footer)
                self.__parse_stylesheet_link(footer)
            return self.result

        def __parse_footer_element(self):
            if not (footers := self.tree.findall('.//footer')):
                self.result.add_error(self.context.path, 'Missing footer')
            elif len(footers) > 1:
                self.result.add_error(self.context.path, 'Multiple footers')
            elif footers[0].getnext() is not None:
                self.result.add_error(self.context.path, 'Footer is not last element')
            else:
                return footers[0]
            return None

        def __parse_horizontal_rule(self, footer):
            if not (rules := footer.findall('./hr')):
                self.result.add_error(self.context.path, 'Footer is missing rule')
            elif len(rules) > 1:
                self.result.add_error(self.context.path, 'Footer has multiple rules')

        def __parse_stylesheet_link(self, footer):
            if not (links := footer.findall('./link')) or links[0].attrib['rel'] != 'stylesheet':
                self.result.add_error(self.context.path, 'Footer is missing stylesheet link')
            elif len(links) > 1:
                self.result.add_error(self.context.path, 'Footer has multiple links')
            else:
                destination = (self.context.path.parent / links[0].attrib['href']).resolve()
                self.context.link = InternalLink(self.context.path, destination)


@lru_cache
def parse_markdown(path: Path) -> HtmlElement:
    return html.fragment_fromstring(
        markdown(path.read_text(encoding='utf-8'), output_format='html'),
        create_parent=True)
