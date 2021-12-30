import sys
from pathlib import Path

from model import Logbook

if __name__ == '__main__':
    logbook = Logbook(Path(sys.argv[1]))
    # noinspection PyTypeChecker
    for e in sorted(logbook.parse().errors):
        print(f'{e.path.relative_to(logbook.root).as_posix()}: {e.message}')
        if e.hint:
            print(e.hint)
