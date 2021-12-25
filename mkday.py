import argparse
import datetime
import sys
from pathlib import Path

from model import Logbook, MarkdownParser, Day


def main(args: argparse.Namespace):
    def adjust_markdown(new_day: Day):
        def rewrite_header_1(day: Day):
            if day:
                lines = day.path.read_text(encoding='utf-8').splitlines()
                lines[0] = day.headers[0].template
                day.path.write_text(MarkdownParser.normalize_markdown('\n'.join(lines)),
                                    encoding='utf-8')

        rewrite_header_1(new_day.previous)
        rewrite_header_1(new_day)
        rewrite_header_1(new_day.next)

    old_logbook = Logbook(args.directory)
    validate(old_logbook)
    if old_logbook.day(args.date) is None:
        Day(args.directory, args.date).save()
        MarkdownParser.invalidate_cache()
        new_logbook = Logbook(args.directory)
        new_logbook.parse()
        adjust_markdown(new_logbook.day(args.date))


def validate(logbook: Logbook):
    parse_result = logbook.parse()
    # noinspection PyTypeChecker
    for e in sorted(parse_result.errors):
        print(f'{e.path.relative_to(logbook.root)}: {e.message}')
        if e.hint:
            print(e.hint)
    if not parse_result.valid:
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path, default=Path.cwd())
    parser.add_argument('-d', '--date', type=datetime.date.fromisoformat,
                        default=datetime.date.today())
    main(parser.parse_args())
