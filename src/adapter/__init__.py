from pathlib import Path
from typing import Protocol, TypedDict

import magic
from typing_extensions import Required

from adapter.base_adapter import Image, Array
from adapter.video_adapter import VideoAdapter, DefaultVideoAdapter


class FileTypeAdapter(Protocol):
    def is_image(self, path: Path) -> bool:
        ...

    def is_audio(self, path: Path) -> bool:
        ...

    def is_video(self, path: Path) -> bool:
        ...


class Digest(Protocol):
    def update(self, data: bytes) -> None:
        ...

    def hexdigest(self) -> str:
        ...


class ImageAdapter(Protocol):
    def load(self, file_path: Path) -> Image:
        ...

    def to_grayscale(self, image: Image) -> Image:
        ...

    def histogram(self, file_path: Path, digest: Digest) -> Image:
        ...

    def rgb_histogram(self, image: Image) -> list[int]:
        ...

    def thumbnail(self, source: Image) -> Image:
        ...

    def fractal_dimension(self, grayscale: Image) -> list[float]:
        ...

    def contrast(self, grayscale: Image) -> float:
        ...

    def saturation_histogram(self, image: Image) -> list[int]:
        ...

    def edge_intensity(self, grayscale: Image) -> float:
        ...

    def colourfulness(self, image: Image) -> float:
        ...

    def sharpness(self, grayscale: Image) -> float:
        ...

    def exposure(self, grayscale: Image) -> float:
        ...

    def vibrance(self, image: Image) -> float:
        ...

    def blurriness(self, image: Image) -> float:
        ...

    def noise(self, grayscale: Image) -> float:
        ...

    def entropy(self, image: Image) -> float:
        ...

    def quadrants(self, image: Image) -> tuple[Image, Image, Image, Image]:
        ...

    def from_data_url(self, data_url: str) -> Image:
        ...


class AudioAdapter(Protocol):
    class Metrics(TypedDict):
        duration: Required[float]
        entropy: Required[float]

    def metrics(self, path: Path) -> Metrics:
        ...


class DefaultFileTypeAdapter(FileTypeAdapter):
    def is_image(self, path: Path) -> bool:
        return self._is_in_category(path, "image")

    def is_audio(self, path: Path) -> bool:
        return self._is_in_category(path, "audio")

    def is_video(self, path: Path) -> bool:
        return self._is_in_category(path, "video")

    @staticmethod
    def _is_in_category(path: Path, category: str) -> bool:
        return (mime := magic.from_file(path, mime=True)) and mime.lower().startswith(
            category
        )


class NullDigest(Digest):
    def update(self, data: bytes) -> None:
        pass

    def hexdigest(self) -> str:
        return "bebacafe"
