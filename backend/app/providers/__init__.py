from app.providers.http_upstream import HttpUpstreamProvider
from app.providers.procedural import ProceduralProvider


def get_provider(name: str, url_template: str = ""):
    if name == "procedural":
        return ProceduralProvider()
    if name == "http_upstream":
        return HttpUpstreamProvider(url_template)
    raise KeyError(f"unknown provider: {name}")
