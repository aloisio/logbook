import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field, InitVar
from pathlib import Path
from typing import List, TypeVar


@dataclass(frozen=True, order=True)
class Error:
    path: Path
    message: str


@dataclass(frozen=True)
class ParseResult:
    errors: List[Error] = field(default_factory=lambda: [])

    @property
    def valid(self) -> bool:
        return not self.errors


class Parsable(metaclass=ABCMeta):
    def parse(self):
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

    class Parser(Parsable.Parser):
        def parse(self) -> ParseResult:
            print(self.context.day)
            return self.result
