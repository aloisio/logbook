import re
import sys
from argparse import ArgumentParser
from functools import cached_property
from hashlib import blake2b
from itertools import filterfalse
from os import stat
from pathlib import Path

from adapters import DefaultImageAdapter, ImageAdapter

CHKSUM_PATTERN = re.compile(r'^.*\.(?P<checksum>[0-9a-fA-F]{16})$')


def _rel(path: Path):
    if path.is_relative_to(Path.cwd()):
        return path.relative_to(Path.cwd())
    return path


def main(write: bool, *patterns: str):
    def file_filter(_path: Path) -> bool:
        return _path.is_absolute() and _path.is_file() and _path.exists()

    paths = list(map(Path, patterns))
    files = filter(file_filter, paths)
    glob_patterns = map(Path.as_posix, filterfalse(Path.is_absolute, paths))
    glob_files = (item for sublist in map(list, map(Path.cwd().glob, glob_patterns))
                  for item in sublist if item.exists() and item.is_file())
    failures = []
    for path in sorted(set(files).union(set(glob_files))):
        checksum = FileMetadataFactory().create(path).checksum
        match = CHKSUM_PATTERN.match(path.stem)
        original_checksum = match.group('checksum') if match else None
        if match and original_checksum == checksum:
            print(f'Checksum OK: {_rel(path)}')
        if match and original_checksum != checksum:
            print(f'Checksum FAIL: {_rel(path)} checksum is {checksum}')
            failures.append(path)
        if not match and not write:
            print(f'Checksum missing: {_rel(path)}')
        if not match and write:
            new_path = path.parent / f'{path.stem}-{checksum}{path.suffix}'
            path.rename(new_path)
            print(f'Checksum added: {_rel(new_path)}')
    return 0 if len(failures) == 0 else 1


# noinspection PyAttributeOutsideInit
class FileMetadata:
    def __init__(self, _path, _image_adapter: ImageAdapter):
        self._image_adapter = _image_adapter
        self.path = _path
        self._checksum = self._image_entropy = self._image_histogram = self._image_size = None
        self._is_image = False

    @property
    def file_size(self) -> int:
        if not hasattr(self, '_byte_size'):
            self._byte_size = stat(self.path).st_size
        return self._byte_size

    @property
    def image_size(self) -> int:
        if not hasattr(self, '_image_size'):
            self._compute_checksum()
        return self._image_size

    @property
    def checksum(self) -> str:
        if not hasattr(self, '_checksum'):
            self._compute_checksum()
        return self._checksum

    @cached_property
    def path_with_checksum(self):
        return self.path.with_name(f'{self.path.stem}.{self.checksum}{self.path.suffix}')

    @property
    def is_image(self) -> bool:
        if not hasattr(self, '_is_image'):
            self._compute_checksum()
        return self._is_image

    @property
    def byte_entropy(self) -> float:
        if not hasattr(self, '_byte_entropy'):
            self._compute_checksum()
        return self._byte_entropy

    @property
    def image_entropy(self) -> float:
        if not hasattr(self, '_byte_entropy'):
            self._compute_checksum()
        return self._image_entropy

    @property
    def byte_histogram(self) -> list[int]:
        if not hasattr(self, '_byte_histogram'):
            self._compute_checksum()
        return self._byte_histogram

    @property
    def byte_fractal_dimension(self) -> list[float]:
        if not hasattr(self, '_byte_thumbnail'):
            self._compute_checksum()
        return self._image_adapter.fractal_dimension(self._byte_thumbnail)

    @property
    def image_histogram(self) -> list[int]:
        if not hasattr(self, '_image_histogram'):
            self._compute_checksum()
        return self._image_histogram

    @cached_property
    def image_fractal_dimension(self) -> list[float]:
        if not hasattr(self, '_image_thumbnail'):
            self._compute_checksum()
        return self._image_adapter.fractal_dimension(self._image_thumbnail)

    def _compute_checksum(self):
        """
        Initializes fields: _byte_histogram, _byte_thumbnail, _checksum, _histogram_entropy,
        _image_entropy, _image_histogram, _image_size, _image_thumbnail, _is_image_
        """
        if self._checksum is not None:
            return
        digest = blake2b(digest_size=8)
        histogram_image = self._image_adapter.histogram(self.path, digest)
        self._byte_entropy = self._image_adapter.last_entropy
        self._byte_histogram = self._image_adapter.rgb_histogram(histogram_image)
        self._byte_thumbnail = self._image_adapter.to_grayscale(histogram_image)
        # noinspection PyBroadException
        try:
            thumbnail_image = self._image_adapter.thumbnail(self.path, digest)
            self._image_size = self._image_adapter.last_size
            self._image_entropy = self._image_adapter.last_entropy
            self._image_histogram = self._image_adapter.rgb_histogram(thumbnail_image)
            self._image_thumbnail = self._image_adapter.to_grayscale(thumbnail_image)
            self._is_image = True
        except Exception:
            self._is_image = False
        self._checksum = digest.hexdigest()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-w', '--write', action='store_true', help='append checksum to file name')
    parser.add_argument('patterns', metavar='FILE', type=str, nargs='+', help='glob pattern for file(s) to check')
    options = parser.parse_args()
    sys.exit(main(options.write, *options.patterns))


class FileMetadataFactory:
    def __init__(self, image_adapter = None):
        self.image_adapter = DefaultImageAdapter() if image_adapter is None else image_adapter

    def create_file_metadata(self, path: Path) -> FileMetadata:
        return FileMetadata(path, self.image_adapter)

    # def create_image_file_metadata(self, path: Path) -> FileMetadata:
    #     return ImageFileMetadata(path, self.image_adapter)