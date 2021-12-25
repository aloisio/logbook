from argparse import ArgumentParser, Namespace
from pathlib import Path

from model import MarkdownParser


def main(args: Namespace):
    content = args.file.read_text(encoding='utf-8')
    args.file.write_text(MarkdownParser.normalize_markdown(content),
                         encoding='utf-8')


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('file', type=Path, default=Path.cwd())
    main(parser.parse_args())
