from argparse import ArgumentParser, Namespace
from pathlib import Path

from model import MarkdownParser


def mdformat(markdown_path: Path):
    content = markdown_path.read_text(encoding='utf-8')
    markdown_path.write_text(MarkdownParser.normalize_markdown(content),
                             encoding='utf-8')


def main(args: Namespace):
    if args.path.is_file():
        mdformat(args.path)
    elif args.path.is_dir():
        for markdown_path in args.path.rglob('*.md'):
            mdformat(markdown_path)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path', type=Path, default=Path.cwd())
    main(parser.parse_args())
