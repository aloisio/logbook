import argparse
import datetime
import sys
from collections import defaultdict
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

        rewrite_header_1(new_day.previous.get('', None))
        rewrite_header_1(new_day)
        rewrite_header_1(new_day.next.get('', None))

    old_logbook = Logbook(args.directory)
    validate(old_logbook)
    # old_logbook.parse()
    if old_logbook.day(args.date) is None:
        Day(args.directory, args.date).save()
        MarkdownParser.invalidate_cache()
        new_logbook = Logbook(args.directory)
        new_logbook.parse()
        adjust_markdown(new_logbook.day(args.date))
        new_logbook.month(args.date).save()
        new_logbook.year(args.date).save()
        new_logbook.save()


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
    parser.add_argument('-d', '--date', type=datetime.date.fromisoformat,
                        default=datetime.date.today())
    main(parser.parse_args())
