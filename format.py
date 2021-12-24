import sys
from pathlib import Path

from model import MarkdownParser


def main(path: Path):
    content = path.read_text(encoding='utf-8')
    path.write_text(MarkdownParser.normalize_markdown(content), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) < 1:
        sys.exit(1)
    main(Path(sys.argv[1]))
