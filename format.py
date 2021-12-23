import sys
from pathlib import Path
from typing import Generator

from markdown_it.token import Token
from mdformat._util import build_mdit
from mdformat.renderer import MDRenderer
from mdformat_gfm.plugin import update_mdit


def main(path: Path):
    parser = build_mdit(renderer_cls=MDRenderer, mdformat_opts={'number': True})
    update_mdit(parser)
    tokens = parser.parse(path.read_text(encoding='utf-8'))
    env = {'references': {}}
    links = list(get_links(tokens))
    link_attributes: dict[tuple[str, str], int] = {}
    for link in links:
        link_attributes.setdefault(attributes_as_tuple(link), len(link_attributes) + 1)
    for link in links:
        index = link_attributes[attributes_as_tuple(link)]
        label = str(index).zfill(len(str(len(link_attributes))))
        link.meta['label'] = label
        env['references'][label] = attributes_as_dict(link)
    path.write_text(parser.renderer.render(tokens, parser.options, env), encoding='utf-8')


def attributes_as_tuple(link: Token) -> tuple[str, str]:
    return link.attrs.get('href', link.attrs.get('src')), link.attrs.get('title', '')


def attributes_as_dict(link: Token) -> dict[str, str]:
    attributes = attributes_as_tuple(link)
    return dict(href=attributes[0], title=attributes[1])


def get_links(tokens: list[Token]) -> Generator[Token, None, None]:
    def is_link(token: Token):
        return token.type == 'link_open' and token.markup != 'autolink'

    def is_image(token: Token):
        return token.type == 'image'

    last_i = len(tokens) - 1
    for i, token in enumerate(tokens):
        if is_link(token) and i < last_i and is_image(tokens[i + 1]):
            yield tokens[i + 1]
            yield token
        elif is_link(token) or is_image(token):
            yield token
        yield from get_links(token.children or [])


if __name__ == '__main__':
    if len(sys.argv) < 1:
        sys.exit(1)
    main(Path(sys.argv[1]))
