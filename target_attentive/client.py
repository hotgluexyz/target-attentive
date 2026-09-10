"""Attentive target sink base class."""

from __future__ import annotations

from typing import Dict, List, Optional

from singer_sdk.plugin_base import PluginBase
from target_hotglue.client import HotglueSink

from target_attentive.auth import get_attentive_authenticator


class AttentiveSink(HotglueSink):
    """Shared Attentive REST sink (auth, base URL, headers)."""

    auth_state = {}
    base_url = "https://api.attentivemobile.com/v1"
    available_names: List[str] = []
    unified_schema = None

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: Dict,
        key_properties: Optional[List[str]],
    ) -> None:
        self._target = target
        super().__init__(target, stream_name, schema, key_properties)

    @property
    def authenticator(self):
        return get_attentive_authenticator(self._target, self.auth_state)

    @property
    def http_headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        headers.update(self.authenticator.auth_headers or {})
        return headers
