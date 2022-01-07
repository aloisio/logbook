import argparse
import sys
from pathlib import Path

from model import Logbook


def main(args: argparse.Namespace):
    validate(Logbook(args.directory))


def validate(logbook: Logbook):
    parse_result = logbook.parse()
    # noinspection PyTypeChecker
    for e in sorted(parse_result.errors):
        print(f'{e.path.relative_to(logbook.root).as_posix()}: {e.message}')
        if e.hint:
            print(e.hint)
    if not parse_result.valid:
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', type=Path,
                        default=Path.cwd())
    main(parser.parse_args())
