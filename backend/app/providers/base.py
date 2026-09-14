from abc import ABC, abstractmethod

from PIL import Image


class TileProvider(ABC):
    """A layer's pixel source. Only 'procedural' is implemented in this repo."""

    name: str

    @abstractmethod
    def render(self, z: int, x: int, y: int) -> Image.Image:
        raise NotImplementedError
