from functools import cached_property
from typing import TypedDict

import numpy as np
from typing_extensions import Required, NotRequired, Unpack

from adapter import Image, ImageAdapter, Array
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
        self._width, self._height = args["image"].size
        quadrants = image_adapter.quadrants(thumbnail_image)
        self._image_entropy = list(
            map(image_adapter.entropy, [thumbnail_image, *quadrants])
        )
        self._image_histogram = image_adapter.rgb_histogram(thumbnail_image)
        grayscale_image = image_adapter.to_grayscale(thumbnail_image)
        gray_quadrants = image_adapter.quadrants(grayscale_image)
        self._contrast = list(
            map(image_adapter.contrast, [grayscale_image, *gray_quadrants])
        )
        self._edge_intensity = list(
            map(image_adapter.edge_intensity, [grayscale_image, *gray_quadrants])
        )
        self._saturation = image_adapter.saturation_histogram(thumbnail_image)
        self._colourfulness = list(
            map(
                image_adapter.colourfulness,
                [
                    thumbnail_image,
                    *quadrants,
                ],
            )
        )
        self._sharpness = list(
            map(image_adapter.sharpness, [grayscale_image, *gray_quadrants])
        )
        self._blurriness = list(
            map(image_adapter.blurriness, [grayscale_image, *gray_quadrants])
        )
        self._exposure = list(
            map(image_adapter.exposure, [grayscale_image, *gray_quadrants])
        )
        self._vibrance = list(
            map(image_adapter.vibrance, [thumbnail_image, *quadrants])
        )
        self._noise = list(map(image_adapter.noise, [grayscale_image, *quadrants]))
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
        return self._image_entropy

    @property
    def contrast(self) -> list[float]:
        return self._contrast

    @property
    def saturation_histogram(self) -> list[int]:
        return self._saturation

    @property
    def edge_intensity(self) -> list[float]:
        return self._edge_intensity

    @property
    def colourfulness(self) -> list[float]:
        return self._colourfulness

    @property
    def sharpness(self) -> list[float]:
        return self._sharpness

    @property
    def blurriness(self) -> list[float]:
        return self._blurriness

    @property
    def exposure(self) -> list[float]:
        return self._exposure

    @property
    def vibrance(self) -> list[float]:
        return self._vibrance

    @property
    def noise(self) -> list[float]:
        return self._noise

    @property
    def vector(self) -> Array:
        return np.array(
            [
                self.width,
                self.height,
                *self.rgb_histogram,
                *self.entropy,
                *self.contrast,
                *self.saturation_histogram,
                *self.edge_intensity,
                *self.colourfulness,
                *self.sharpness,
                *self.blurriness,
                *self.exposure,
                *self.vibrance,
                *self.noise,
                *self.fractal_dimension,
            ]
        )


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
