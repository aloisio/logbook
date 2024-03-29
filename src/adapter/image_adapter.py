from base64 import b64decode
from hashlib import blake2b
from io import BytesIO
from pathlib import Path
from typing import TypedDict

import PIL.Image
import numpy as np
from PIL import Image
from PIL import ImageFilter, ImageStat
from scipy.ndimage import convolve
from scipy.signal import convolve2d
from scipy.stats import skew, kurtosis
from typing_extensions import NotRequired, Unpack

import fracdim
from adapter import ImageAdapter, Digest


class DefaultImageAdapter(ImageAdapter):
    class Arguments(TypedDict):
        digest: NotRequired[Digest]

    def __init__(self, **kwargs: Unpack[Arguments]):
        kwargs = self.Arguments(**kwargs)
        self._digest = (
            kwargs["digest"] if "digest" in kwargs else blake2b(digest_size=16)
        )

    def load(self, file_path: Path) -> Image:
        return PIL.Image.open(file_path)

    def histogram(self, file_path: Path) -> tuple[Image, str]:
        digest = self._digest.copy()
        hist = np.zeros((256, 256), dtype=np.uint8)
        with file_path.open("rb") as f:
            while chunk := f.read(32 * 1024 * 1024):
                digest.update(chunk)
                np.frombuffer(chunk, dtype=np.uint8)
                data = np.frombuffer(chunk, dtype=np.uint8)
                x = data[:-1]
                y = data[1:]
                np.add.at(hist, (x, y), 1)

        hist = (hist * 0xFFFFFF) // np.clip(hist.max(initial=0), a_min=1, a_max=None)
        rgb_hist = np.array(
            [(hist >> 16) & 0xFF, (hist >> 8) & 0xFF, hist & 0xFF], dtype=np.uint8
        ).transpose((1, 2, 0))

        histogram_image = PIL.Image.fromarray(rgb_hist, "RGB")
        return histogram_image, digest.hexdigest()

    def thumbnail(self, source: Image) -> Image:
        thumbnail_image: PIL.Image = source.convert(mode="RGB").resize(
            (256, 256), PIL.Image.BICUBIC
        )
        return thumbnail_image

    def fractal_dimension(self, grayscale: Image) -> list[float]:
        # noinspection PyTypeChecker
        return [
            fracdim.fractal_dimension(np.array(grayscale), level)
            for level in range(0, 256, 4)
        ]

    def contrast(self, grayscale: Image) -> float:
        histogram = grayscale.histogram()
        pixels = grayscale.size[0] * grayscale.size[1]

        # calculate the pixel intensities that represent the darkest and brightest parts of the image
        darkest_pixels = 0
        brightest_pixels = 0
        for i in range(0, 256):
            darkest_pixels += histogram[i]
            if darkest_pixels > pixels * 0.01:
                break
        for i in range(255, -1, -1):
            brightest_pixels += histogram[i]
            if brightest_pixels > pixels * 0.01:
                break

        # calculate the contrast for the grayscale image
        contrast = (brightest_pixels - darkest_pixels) / pixels

        return contrast

    def to_grayscale(self, image: Image) -> Image:
        return image.convert("L")

    def rgb_histogram(self, image: Image) -> list[int]:
        return image.histogram()

    def saturation_histogram(self, image: Image) -> list[int]:
        # Convert the image to the HSV color space
        return image.convert("HSV").split()[1].histogram()

    def edge_intensity(self, grayscale: Image) -> float:
        # Apply the FIND_EDGES filter to detect edges
        edges = grayscale.filter(ImageFilter.FIND_EDGES)

        # Calculate the mean pixel value of the edges image
        return sum(edges.getdata()) / len(edges.getdata())

    # noinspection PyTypeChecker
    def colourfulness(self, image: Image) -> float:
        """
        Calculate the colorfulness metric of an image using the PIL Image class.
        :param image: PIL Image object
        :return: float colorfulness value
        """
        # Convert the image to the LAB color space
        image_lab = image.convert("LAB")

        # Split the LAB channels
        L, A, B = image_lab.split()

        # Calculate the standard deviation of the A and B channels
        A_std = np.std(np.asarray(A))
        B_std = np.std(np.asarray(B))

        # Calculate the mean of the standard deviations
        std_root = np.sqrt((A_std**2) + (B_std**2))
        mean_root = np.sqrt(np.mean(np.asarray(L)))

        # Calculate the colorfulness metric
        colorfulness = std_root + (0.3 * mean_root)

        return colorfulness

    def sharpness(self, grayscale: Image) -> float:
        # Convert PIL Image to numpy array
        # noinspection PyTypeChecker
        img_arr = np.array(grayscale)

        # Compute Laplacian using 3x3 filter kernel
        laplacian_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        laplacian = np.abs(convolve2d(img_arr, laplacian_kernel, mode="same"))

        # Compute the sharpness as the variance of the Laplacian
        sharpness = np.var(laplacian)

        return sharpness.item()

    def blurriness(self, grayscale: Image) -> float:
        # Convert PIL Image to numpy array
        # noinspection PyTypeChecker
        img_arr = np.array(grayscale)

        # Apply Laplacian of Gaussian filter
        log_kernel = np.array(
            [
                [0, 0, -1, 0, 0],
                [0, -1, -2, -1, 0],
                [-1, -2, 16, -2, -1],
                [0, -1, -2, -1, 0],
                [0, 0, -1, 0, 0],
            ]
        )
        log_filter = convolve(img_arr, log_kernel)

        # Compute the blurriness as the variance of the LoG filter response
        blurriness = np.var(log_filter)

        return blurriness.item()

    def noise(self, grayscale: Image) -> float:
        # Convert PIL image to numpy array
        # noinspection PyTypeChecker
        img_arr = np.array(grayscale)

        # Compute the standard deviation of the pixel intensities
        stddev = np.std(img_arr)

        # If the standard deviation is zero, return a noise level of zero
        if stddev == 0:
            return 0

        # Compute the skewness and kurtosis of the pixel intensities
        skewness = skew(img_arr.flatten())
        kurt = kurtosis(img_arr.flatten())

        # Compute the noise level as a function of the standard deviation,
        # skewness, and kurtosis
        noise = np.sqrt(stddev**2 + 0.1 * (skewness**2 + kurt**2))

        return noise

    def exposure(self, grayscale: Image) -> float:
        # Compute the average luminance using ImageStat
        luminance = ImageStat.Stat(grayscale).mean[0]
        # Compute the exposure as the inverse of the luminance
        if luminance != 0:
            return 1.0 / luminance
        # Return a default exposure value if the image is completely black
        return 0

    # noinspection PyTypeChecker
    def vibrance(self, image: Image) -> float:
        """
        Computes the vibrance of the given image.
        """
        # Convert the image to the Lab color space
        lab_image = image.convert("LAB")

        # Split the image into its three channels
        l_channel, a_channel, b_channel = lab_image.split()

        # Compute the standard deviation of the a and b channels
        a_std = np.std(np.array(a_channel))
        b_std = np.std(np.array(b_channel))

        # Compute the vibrance as the average of the standard deviations
        vibrance = np.mean([a_std, b_std])

        return vibrance.item()

    def entropy(self, image: Image) -> float:
        return image.entropy()

    def quadrants(self, image: Image) -> tuple[Image, Image, Image, Image]:
        width, height = image.size
        # Calculate the coordinates of the four sub-images
        top_left = (0, 0, width // 2, height // 2)
        top_right = (width // 2, 0, width, height // 2)
        bottom_left = (0, height // 2, width // 2, height)
        bottom_right = (width // 2, height // 2, width, height)

        # Crop the original image to get each sub-image
        return (
            image.crop(top_left),
            image.crop(top_right),
            image.crop(bottom_left),
            image.crop(bottom_right),
        )

    def from_data_url(self, data_url: str) -> Image:
        image_data = b64decode(data_url.split(",")[1])
        return Image.open(BytesIO(image_data))

    def checksum(self, image: Image) -> str:
        digest = self._digest.copy()
        digest.update(image.tobytes())
        return digest.hexdigest()

    @staticmethod
    def _to_bytes(image: Image) -> bytes:
        # noinspection PyTypeChecker
        return np.array(image).flatten().tobytes()
