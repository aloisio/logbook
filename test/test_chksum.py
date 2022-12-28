import hashlib

from chksum import chksum


def test_checksum_of_empty_file(tmp_path):
    empty_file = tmp_path / 'test.txt'
    empty_file.touch()
    assert chksum(empty_file) == hashlib.blake2b(''.encode(), digest_size=2).hexdigest()


def test_checksum_of_non_empty_file(tmp_path):
    empty_file = tmp_path / 'test.txt'
    empty_file.write_text('Hello World')
    assert chksum(empty_file) == hashlib.blake2b('Hello World'.encode(), digest_size=2).hexdigest()
