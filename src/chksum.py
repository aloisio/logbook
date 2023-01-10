import hashlib
import re
import sys
from argparse import ArgumentParser
from itertools import filterfalse
from pathlib import Path

CHKSUM_PATTERN = re.compile(r'^.*-(?P<checksum>[0-9a-fA-F]{4})$')


def chksum(path: Path) -> str:
    blake2b = hashlib.blake2b(digest_size=2)
    with path.open('rb') as input_file:
        while buffer := input_file.read(2 ** 20):
            blake2b.update(buffer)
    return blake2b.hexdigest()


def _rel(path: Path):
    if path.is_relative_to(Path.cwd()):
        return path.relative_to(Path.cwd())
    return path


def main(write: bool, *patterns: str):
    def file_filter(path: Path) -> bool:
        return path.is_absolute() and path.is_file() and path.exists()

    paths = list(map(Path, patterns))
    files = filter(file_filter, paths)
    glob_patterns = map(Path.as_posix, filterfalse(Path.is_absolute, paths))
    glob_files = (item for sublist in map(list, map(Path.cwd().glob, glob_patterns))
                  for item in sublist if item.exists() and item.is_file())
    failures = []
    for path in sorted(set(files).union(set(glob_files))):
        checksum = chksum(path)
        match = CHKSUM_PATTERN.match(path.stem)
        original_checksum = match.group('checksum') if match else None
        if match and original_checksum == checksum:
            print(f'Checksum OK: {_rel(path)}')
        if match and original_checksum != checksum:
            print(f'Checksum FAIL: {_rel(path)} checksum is {checksum}')
            failures.append(path)
        if not match and not write:
            print(f'Checksum missing: {_rel(path)}')
        if not match and write:
            new_path = path.parent / f'{path.stem}-{chksum(path)}{path.suffix}'
            path.rename(new_path)
            print(f'Checksum added: {_rel(new_path)}')
    return 0 if len(failures) == 0 else 1


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-w', '--write', action='store_true', help='append checksum to file name')
    parser.add_argument('patterns', metavar='FILE', type=str, nargs='+', help='glob pattern for file(s) to check')
    options = parser.parse_args()
    sys.exit(main(options.write, *options.patterns))
