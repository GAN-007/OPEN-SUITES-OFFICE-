from nexus_workspace.models import EngineName, RouteRequest
from nexus_workspace.routing import CapabilityRouter


def test_temporal_query_routes_to_graphiti() -> None:
    result = CapabilityRouter().route(RouteRequest(intent="What was the approved limit before it changed in March?"))
    assert result.engine == EngineName.GRAPHITI


def test_long_document_query_routes_to_pageindex() -> None:
    result = CapabilityRouter().route(RouteRequest(intent="Compare section 18.4 with appendix C in this 900 page report"))
    assert result.engine == EngineName.PAGEINDEX


def test_browser_action_routes_to_browser_use() -> None:
    result = CapabilityRouter().route(RouteRequest(intent="Open the website, fill the form and click submit"))
    assert result.engine == EngineName.BROWSER_USE


def test_unknown_query_routes_to_open_webui() -> None:
    result = CapabilityRouter().route(RouteRequest(intent="Explain quantum entanglement"))
    assert result.engine == EngineName.OPEN_WEBUI
