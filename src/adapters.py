import struct
from pathlib import Path
from typing import Protocol, Optional

import PIL.Image
import librosa
import magic
import numpy as np

import fracdim

Image = PIL.Image.Image

Array = np.array


class Digest(Protocol):
    def update(self, data: bytes) -> None:
        ...

    def hexdigest(self) -> str:
        ...


class ImageAdapter(Protocol):

    def to_grayscale(self, image: Image) -> Array:
        ...

    def histogram(self, file_path: Path, digest: Digest) -> Image:
        ...

    def rgb_histogram(self, image: Image) -> list[int]:
        ...

    def thumbnail(self, path: Path) -> Image:
        ...

    def fractal_dimension(self, grayscale: Array) -> list[float]:
        ...

    @property
    def last_entropy(self) -> Optional[float]:
        raise NotImplemented

    @property
    def last_size(self) -> Optional[tuple[int, int]]:
        raise NotImplemented


class AudioAdapter(Protocol):
    def duration(self, path: Path) -> float:
        ...


class NullDigest(Digest):
    def update(self, data: bytes) -> None:
        pass

    def hexdigest(self) -> str:
        return 'bebacafe'


class DefaultImageAdapter(ImageAdapter):
    def __init__(self):
        self._last_size: Optional[tuple[int, int]] = None
        self._last_entropy: Optional[float] = None

    def histogram(self, file_path: Path, digest: Digest = None) -> Image:
        digest = digest if digest is not None else NullDigest()
        hist = np.zeros((256, 256), dtype=np.uint8)
        with file_path.open('rb') as f:
            while chunk := f.read(32 * 1024 * 1024):
                digest.update(chunk)
                np.frombuffer(chunk, dtype=np.uint8)
                data = np.frombuffer(chunk, dtype=np.uint8)
                x = data[:-1]
                y = data[1:]
                np.add.at(hist, (x, y), 1)

        hist = ((hist * 0xFFFFFF) // np.clip(hist.max(initial=0), a_min=1, a_max=None))
        rgb_hist = Array([(hist >> 16) & 0xFF, (hist >> 8) & 0xFF, hist & 0xFF], dtype=np.uint8).transpose((1, 2, 0))
        histogram_image = PIL.Image.fromarray(rgb_hist, 'RGB')
        digest.update(self._to_bytes(histogram_image))
        entropy = histogram_image.entropy()
        self._last_entropy = entropy
        digest.update(struct.pack('<f', entropy))
        return histogram_image

    def thumbnail(self, path: Path) -> Image:
        with PIL.Image.open(path) as image:
            thumbnail_image: PIL.Image = image.convert(mode='RGB').resize((256, 256), PIL.Image.BICUBIC)
            self._last_entropy = image.entropy()
            self._last_size = image.size
        return thumbnail_image

    @property
    def last_entropy(self) -> Optional[float]:
        return self._last_entropy

    @property
    def last_size(self) -> Optional[tuple[int, int]]:
        return self._last_size

    def fractal_dimension(self, grayscale: Array) -> list[float]:
        return [fracdim.fractal_dimension(grayscale, level) for level in range(0, 256)]

    def to_grayscale(self, image: Image) -> Array:
        # noinspection PyTypeChecker
        return Array(image.convert('L'))

    def rgb_histogram(self, image: Image) -> list[int]:
        return image.histogram()

    @staticmethod
    def _to_bytes(image: Image) -> bytes:
        # noinspection PyTypeChecker
        return Array(image).flatten().tobytes()


class DefaultAudioAdapter(AudioAdapter):
    def duration(self, path: Path) -> float:
        y, sr = librosa.load(path.as_posix())
        return librosa.get_duration(y=y, sr=sr)


class FileTypeAdapter(Protocol):
    def is_image(self, path: Path) -> bool:
        ...

    def is_audio(self, path: Path) -> bool:
        ...


class DefaultFileTypeAdapter(FileTypeAdapter):
    def is_image(self, path: Path) -> bool:
        return (mime := magic.from_file(path, mime=True)) and mime.startswith('image')

    def is_audio(self, path: Path) -> bool:
        return (mime := magic.from_file(path, mime=True)) and mime.startswith('audio')
