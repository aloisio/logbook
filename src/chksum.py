import re
import sys
from argparse import ArgumentParser
from itertools import filterfalse
from pathlib import Path

from metadata import FileMetadataFactory, FileMetadata

CHKSUM_PATTERN = re.compile(r"^.*\.(?P<checksum>[0-9a-fA-F]{16})$")


def _rel(path: Path):
    if path.is_relative_to(Path.cwd()):
        return path.relative_to(Path.cwd())
    return path


def main(write: bool, *patterns: str):
    def file_filter(_path: Path) -> bool:
        return _path.is_absolute() and _path.is_file() and _path.exists()

    paths = list(map(Path, patterns))
    files = filter(file_filter, paths)
    glob_patterns = map(Path.as_posix, filterfalse(Path.is_absolute, paths))
    glob_files = (
        item
        for sublist in map(list, map(Path.cwd().glob, glob_patterns))
        for item in sublist
        if item.exists() and item.is_file()
    )
    failures = []
    for path in sorted(set(files).union(set(glob_files))):
        checksum = FileMetadataFactory().create_metadata(path)[FileMetadata].checksum
        match = CHKSUM_PATTERN.match(path.stem)
        original_checksum = match.group("checksum") if match else None
        if match and original_checksum == checksum:
            print(f"Checksum OK: {_rel(path)}")
        if match and original_checksum != checksum:
            print(f"Checksum FAIL: {_rel(path)} checksum is {checksum}")
            failures.append(path)
        if not match and not write:
            print(f"Checksum missing: {_rel(path)}")
        if not match and write:
            new_path = path.parent / f"{path.stem}-{checksum}{path.suffix}"
            path.rename(new_path)
            print(f"Checksum added: {_rel(new_path)}")
    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-w", "--write", action="store_true", help="append checksum to file name"
    )
    parser.add_argument(
        "patterns",
        metavar="FILE",
        type=str,
        nargs="+",
        help="glob pattern for file(s) to check",
    )
    options = parser.parse_args()
    sys.exit(main(options.write, *options.patterns))
