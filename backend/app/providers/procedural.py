from PIL import Image, ImageDraw

from app.providers.base import TileProvider


class ProceduralProvider(TileProvider):
    name = "procedural"

    def render(self, z: int, x: int, y: int) -> Image.Image:
        color = (
            36 + (x * 47) % 200,
            48 + (y * 31) % 180,
            64 + (z * 40) % 140,
        )
        img = Image.new("RGB", (256, 256), color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (255, 255)], outline=(20, 24, 32), width=2)
        draw.text((18, 36), f"z {z}", fill="white")
        draw.text((18, 66), f"x {x}", fill="white")
        draw.text((18, 96), f"y {y}", fill="white")
        return img
