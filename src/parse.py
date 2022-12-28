import argparse
import sys
from collections import defaultdict
from pathlib import Path

from model import Logbook


def main(args: argparse.Namespace):
    validate(Logbook(args.directory))


def validate(logbook: Logbook):
    parse_result = logbook.parse()
    errors = defaultdict(list)
    # noinspection PyTypeChecker
    for e in sorted(parse_result.errors):
        errors[e.path].append(e)
    for errs in errors.values():
        print(f'[{errs[0].path.relative_to(logbook.root).as_posix()}]')
        for e in errs:
            print(f'> {e.message}')
            if e.hint:
                print(e.hint)
    if not parse_result.valid:
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', type=Path,
                        default=Path.cwd())
    main(parser.parse_args())
