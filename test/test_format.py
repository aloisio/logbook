from pathlib import Path
from textwrap import dedent

from format import main


def test_move_inline_links_to_link_references(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        # [❮](../prev.md) [Header](../top.md "Top") [❯](../next.md)
        
        paragraph
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        # [❮][1] [Header][2] [❯][3]
        
        paragraph

        [1]: ../prev.md
        [2]: ../top.md "Top"
        [3]: ../next.md
    ''')


def test_detect_duplicates(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        # [❮](linked.md) [Header](../top.md "Top") [❯](linked.md)

        paragraph
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        # [❮][1] [Header][2] [❯][1]

        paragraph

        [1]: linked.md
        [2]: ../top.md "Top"
    ''')


def test_zero_fill_link_reference_labels(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        # [A](a) [B](b) [C](c) [D](d) [E](e) [F](f) [G](g) [H](h) [I](i) [J](j)

        paragraph
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        # [A][01] [B][02] [C][03] [D][04] [E][05] [F][06] [G][07] [H][08] [I][09] [J][10]

        paragraph

        [01]: a
        [02]: b
        [03]: c
        [04]: d
        [05]: e
        [06]: f
        [07]: g
        [08]: h
        [09]: i
        [10]: j
    ''')


def test_rearrange_existing_link_reference_definitions(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        # [A](a) [B][1] [C](c) [D](c)

        paragraph
        
        [1]: b
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        # [A][1] [B][2] [C][3] [D][3]

        paragraph

        [1]: a
        [2]: b
        [3]: c
    ''')


def test_image_links(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        ![Alt](image.jpg "title")
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        ![Alt][1]

        [1]: image.jpg "title"
    ''')


def test_autolink_does_not_create_link_reference_definition(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        ## Test
        
        > Test <email@example.com>
        >
        > ![test](image.jpg)
        >
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        ## Test
        
        > Test <email@example.com>
        >
        > ![test][1]
        
        [1]: image.jpg
    ''')


def test_auto_links_are_skipped(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        Go to <https://www.google.com>
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        Go to <https://www.google.com>
    ''')


def test_number_nested_links_depth_first(tmp_path):
    tmp_file(tmp_path).write_text(content('''
        [![Alt](image.jpg "title")](external.md) [Figure 1](list_of_figures.md)
    '''))
    main(tmp_file(tmp_path))
    assert tmp_file(tmp_path).read_text() == content('''
        [![Alt][1]][2] [Figure 1][3]
        
        [1]: image.jpg "title"
        [2]: external.md
        [3]: list_of_figures.md
    ''')


def tmp_file(directory: Path):
    return directory / 'test.md'


def content(multiline_text):
    return dedent(multiline_text).lstrip()
