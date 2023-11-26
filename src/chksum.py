import hashlib
import mmap
import re
import sys
import traceback
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TypedDict, Protocol, cast, Generator, Callable, Optional


@dataclass
class Checksum:
    path: Path
    value: str

    def __str__(self) -> str:
        return self.value


class CommandRequest(TypedDict):
    write: bool
    delete: bool
    files: list[Path]


class CommandResponse(TypedDict):
    success: bool


class InputHandler(Protocol):
    def command_request(self) -> CommandRequest:
        ...


class Presenter(Protocol):
    def ok(self, checksum: Checksum) -> None:
        ...

    def fail(self, checksum: Checksum) -> None:
        ...

    def added(self, new_checksum: Checksum) -> None:
        ...

    def deleted(self, new_checksum: Checksum) -> None:
        ...

    def show(self, checksum: Checksum) -> None:
        ...

    def error(self) -> None:
        ...


class Digester(Protocol):
    @property
    def valid_chars(self) -> str:
        return ...

    @property
    def length(self) -> int:
        return ...

    def compute_digest(self, file: Path) -> Checksum:
        ...


class QuarterSha256Base36Digester(Digester):
    @property
    def valid_chars(self) -> str:
        return "0-9a-z"

    @property
    def length(self) -> int:
        return 13

    def compute_digest(self, file: Path) -> Checksum:
        # Create an instance of the SHA256 hash algorithm
        hash_algorithm = hashlib.sha256()

        if file.stat().st_size > 0:
            with open(file, "rb") as input_file:
                with mmap.mmap(
                    input_file.fileno(), 0, access=mmap.ACCESS_READ
                ) as mmapped_file:
                    hash_algorithm.update(mmapped_file)

        # Obtain the digest or hash value
        digest = hash_algorithm.digest()
        # Convert the first quarter of the digest to a decimal number
        decimal_number = int.from_bytes(
            digest[0 : len(digest) // 4], byteorder="big", signed=False
        )
        # Convert the decimal number to base-36, left-zero fill
        checksum = self.base_36(decimal_number).zfill(self.length)

        return Checksum(file, checksum)

    @staticmethod
    def base_36(number) -> str:
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"

        num = abs(number)
        res = []
        while num:
            res.append(digits[num % 36])
            num //= 36
        if number < 0:
            res.append("-")
        return "".join(reversed(res or "0"))


class ChecksumRepository(Protocol):
    def has_checksum(self, file: Path) -> bool:
        ...

    def checksum(self, file: Path) -> Checksum:
        ...

    def write_checksum(self, checksum: Checksum) -> Checksum:
        ...

    def delete_checksum(self, checksum: Checksum) -> Checksum:
        ...


class FileRenamer(ChecksumRepository):
    def __init__(self, digester: Digester):
        self.checksum_pattern = re.compile(
            r"^(?P<prefix>.*?)\."
            rf"(?P<checksum>[{digester.valid_chars}]{{{digester.length}}})"
            r"(?P<suffix>\..*)?$",
            re.IGNORECASE,
        )

    def has_checksum(self, file: Path) -> bool:
        return bool(self.checksum_pattern.fullmatch(file.name))

    def checksum(self, file: Path) -> Checksum:
        if match := self.checksum_pattern.fullmatch(file.name):
            return Checksum(file, match.group("checksum").lower())
        raise ValueError(f"No checksum: {file}")

    def write_checksum(self, checksum: Checksum) -> Checksum:
        file = checksum.path
        if not self.has_checksum(file):
            new_path = file.parent / f"{file.stem}.{checksum}{file.suffix}"
            file.rename(new_path)
            return Checksum(new_path, checksum.value)
        return checksum

    def delete_checksum(self, checksum: Checksum) -> Checksum:
        file = checksum.path
        if self.has_checksum(file):
            match = self.checksum_pattern.fullmatch(file.name)
            if new_file_name := f"{match.group('prefix')}{match.group('suffix') or ''}":
                new_path = file.parent / new_file_name
                file.rename(new_path)
                return Checksum(new_path, checksum.value)
        return checksum


class ConsolePresenter(Presenter):
    def ok(self, checksum: Checksum) -> None:
        print(f"Checksum OK\t{checksum}\t{self._rel(checksum)}")

    def fail(self, checksum: Checksum) -> None:
        print(f"Checksum FAIL\t{checksum}\t{self._rel(checksum)}")

    def added(self, new_checksum: Checksum) -> None:
        print(f"Checksum ADD\t{new_checksum}\t{self._rel(new_checksum)}")

    def deleted(self, new_checksum: Checksum) -> None:
        print(f"Checksum DEL\t{new_checksum}\t{self._rel(new_checksum)}")

    def show(self, checksum: Checksum) -> None:
        print(f"Checksum IS\t{checksum}\t{self._rel(checksum)}")

    def error(self) -> None:
        traceback.print_exc()

    @staticmethod
    def _rel(checksum: Checksum):
        if checksum.path.is_relative_to(Path.cwd()):
            return checksum.path.relative_to(Path.cwd())
        return checksum.path


class ChecksumCalculator(Protocol):
    @abstractmethod
    def compute_checksums(self, files: list[Path]) -> Generator[Checksum, None, None]:
        ...


class CommandArgs(CommandRequest):
    digester: Digester
    presenter: Presenter
    repository: ChecksumRepository
    calculator: ChecksumCalculator


class Command(ABC):
    def __init__(self, **kwargs):
        kwargs = cast(CommandArgs, kwargs)
        self.presenter = kwargs["presenter"]
        self.repository = kwargs["repository"]
        self.calculator = kwargs["calculator"]
        self.request = cast(CommandRequest, kwargs)

    def run(self) -> CommandResponse:
        try:
            for checksum in self.calculator.compute_checksums(self.request["files"]):
                self.process(checksum)
            return {"success": True}
        except Exception:
            self.presenter.error()
            return {"success": False}

    @abstractmethod
    def process(self, checksum: Checksum) -> None:
        ...


class CommandFactory:
    def __init__(self, /, input_handler: InputHandler, **command_args):
        command_args = cast(CommandArgs, command_args)
        self.command_args = command_args
        self.calculator = command_args["calculator"]
        self.repository = command_args["repository"]
        self.input_handler = input_handler

    def create(self) -> list[Command]:
        def does_not_have_checksum(f: Path):
            return not self.repository.has_checksum(f)

        request = self.input_handler.command_request()
        files = request["files"]
        write_flag = request["write"]
        delete_flag = request["delete"]
        return [
            CheckCommand(
                **self.command_args,
                files=self._filter_files(
                    files, self.repository.has_checksum, not delete_flag
                ),
            ),
            DeleteCommand(
                **self.command_args,
                files=self._filter_files(
                    files, self.repository.has_checksum, delete_flag
                ),
            ),
            ComputeCommand(
                **self.command_args,
                files=self._filter_files(files, does_not_have_checksum, not write_flag),
            ),
            WriteCommand(
                **self.command_args,
                files=self._filter_files(files, does_not_have_checksum, write_flag),
            ),
        ]

    @staticmethod
    def _filter_files(
        files: list[Path],
        repository_condition: Callable[[Path], bool],
        input_condition: bool,
    ) -> list[Path]:
        return [f for f in files if repository_condition(f) and input_condition]


class CheckCommand(Command):
    def process(self, checksum: Checksum) -> None:
        if self.repository.has_checksum(checksum.path):
            if self.repository.checksum(checksum.path) == checksum:
                self.presenter.ok(checksum)
            else:
                self.presenter.fail(checksum)
        else:
            self.presenter.show(checksum)


class ComputeCommand(Command):
    def process(self, checksum: Checksum) -> None:
        self.presenter.show(checksum)


class WriteCommand(Command):
    def process(self, checksum: Checksum) -> None:
        if not self.repository.has_checksum(checksum.path):
            self._add_checksum(checksum)
        else:
            self.presenter.show(checksum)

    def _add_checksum(self, checksum):
        try:
            self.presenter.added(self.repository.write_checksum(checksum))
        except Exception:
            self.presenter.show(checksum)


class DeleteCommand(Command):
    def process(self, checksum: Checksum) -> None:
        if self.repository.has_checksum(checksum.path):
            self._delete_checksum(checksum)
        else:
            self.presenter.show(checksum)

    def _delete_checksum(self, checksum):
        expected_checksum = self.repository.checksum(checksum.path)
        if checksum == expected_checksum:
            try:
                self.presenter.deleted(self.repository.delete_checksum(checksum))
            except Exception:
                self.presenter.ok(checksum)
        else:
            self.presenter.fail(checksum)


class ProcessPoolChecksumCalculator(ChecksumCalculator):
    def __init__(self, digester: Digester):
        self.digester = digester

    def compute_checksums(self, files: list[Path]) -> Generator[Checksum, None, None]:
        with ProcessPoolExecutor() as executor:
            # Submit tasks and get futures
            futures = {
                executor.submit(self.digester.compute_digest, f): f for f in files
            }
            # Use as_completed to yield results as they become available
            for future in as_completed(futures):
                yield future.result()


class CommandLineInputHandler(InputHandler):
    def command_request(self) -> CommandRequest:
        return {
            "files": list(filter(None, self.args.files)),
            "write": self.args.write,
            "delete": self.args.delete,
        }

    @cached_property
    def args(self) -> Namespace:
        def only_files(arg: str) -> Optional[Path]:
            path = Path(arg)
            return path if path.exists() and path.is_file() else None

        parser = ArgumentParser(description="Process a list of files.")
        parser.add_argument(
            "-w",
            "--write",
            action="store_true",
            help="append checksum to file name if not present",
        )
        parser.add_argument(
            "-d",
            "--delete",
            action="store_true",
            help="remove checksum from file name if present",
        )
        parser.add_argument(
            "files",
            type=only_files,
            nargs="*",
            help="List of files or a glob pattern.",
        )
        return parser.parse_args()


class Main:
    def __init__(self):
        digester = QuarterSha256Base36Digester()
        self.command_factory = CommandFactory(
            presenter=ConsolePresenter(),
            input_handler=CommandLineInputHandler(),
            calculator=ProcessPoolChecksumCalculator(digester),
            repository=FileRenamer(digester),
        )

    def run(self) -> int:
        runs = [c.run() for c in self.command_factory.create()]
        return max([0 if r["success"] else 1 for r in runs])


if __name__ == "__main__":
    sys.exit(Main().run())
