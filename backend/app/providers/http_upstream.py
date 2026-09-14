"""
0-1 扩展点：从远程 TMS/XYZ 拉瓦写入本地缓存。

接口已经挂到 GET/POST /api/layers/{slug}/upstream。
实现时应：按 layer.provider_url 请求上游、校验 Content-Type、
按 layer.default_scheme 换算 y、写入 cache.write_tile，并处理超时与 404。
"""

from app.providers.base import TileProvider
from PIL import Image


class HttpUpstreamProvider(TileProvider):
    name = "http_upstream"

    def __init__(self, url_template: str = ""):
        self.url_template = url_template

    def render(self, z: int, x: int, y: int) -> Image.Image:
        raise NotImplementedError(
            "HttpUpstreamProvider 未实现。需要按 url_template 拉取上游瓦片。"
        )
