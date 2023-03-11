from functools import cached_property
from typing import TypedDict

from typing_extensions import Required, NotRequired, Unpack

from adapter import Image, ImageAdapter
from metadata.metadata_base import Metadata


class ImageMetadata(Metadata):
    class Arguments(TypedDict):
        image: Required[Image]
        image_adapter: Required[ImageAdapter]
        fractal_dimension: NotRequired[bool]

    def __init__(self, **kwargs: Unpack[Arguments]):
        args = self.Arguments(**kwargs)
        image_adapter = args["image_adapter"]
        thumbnail_image = image_adapter.thumbnail(args["image"])
        self._width, self._height = image_adapter.last_size
        self._image_entropy = image_adapter.last_entropy
        self._image_histogram = image_adapter.rgb_histogram(thumbnail_image)
        grayscale_image = image_adapter.to_grayscale(thumbnail_image)
        self._contrast = image_adapter.contrast(grayscale_image)
        self._edge_intensity = image_adapter.edge_intensity(grayscale_image)
        self._saturation = image_adapter.saturation_histogram(thumbnail_image)
        self._colourfulness = image_adapter.colourfulness(thumbnail_image)
        self._sharpness = image_adapter.sharpness(grayscale_image)
        self._blurriness = image_adapter.blurriness(grayscale_image)
        self._exposure = image_adapter.exposure(grayscale_image)
        self._vibrance = image_adapter.vibrance(thumbnail_image)
        self._noise = image_adapter.noise(grayscale_image)
        self._fractal_dimension = (
            image_adapter.fractal_dimension(grayscale_image)
            if args.get("fractal_dimension", False)
            else []
        )

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fractal_dimension(self) -> list[float]:
        return self._fractal_dimension

    @property
    def rgb_histogram(self) -> list[int]:
        return self._image_histogram

    @property
    def entropy(self) -> list[float]:
        return [self._image_entropy]

    @property
    def contrast(self) -> float:
        return self._contrast

    @property
    def saturation_histogram(self) -> list[int]:
        return self._saturation

    @property
    def edge_intensity(self) -> float:
        return self._edge_intensity

    @property
    def colourfulness(self) -> float:
        return self._colourfulness

    @property
    def sharpness(self) -> float:
        return self._sharpness

    @property
    def blurriness(self) -> float:
        return self._blurriness

    @property
    def exposure(self) -> float:
        return self._exposure

    @property
    def vibrance(self) -> float:
        return self._vibrance

    @property
    def noise(self) -> float:
        return self._noise


class ImageFileMetadata(Metadata):
    def __init__(self, path, image_adapter: ImageAdapter):
        self._path = path
        self._image_adapter = image_adapter

    @cached_property
    def image_metadata(self) -> ImageMetadata:
        return ImageMetadata(
            image=self._image_adapter.load(self._path),
            image_adapter=self._image_adapter,
            fractal_dimension=True,
        )
