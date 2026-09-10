"""Attentive target class."""

from __future__ import annotations

from singer_sdk import typing as th
from target_hotglue.target import TargetHotglue

from target_attentive.sinks import EventsSink, ProfilesSink


class TargetAttentive(TargetHotglue):
    """Singer target for Attentive."""

    name = "target-attentive"
    SINK_TYPES = [ProfilesSink, EventsSink]
    MAX_PARALLELISM = 1

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            description="Attentive private app API key (Bearer token)",
        ),
    ).to_dict()

    def get_sink_class(self, stream_name: str):
        """Route stream names to Profiles or Events sinks."""
        for sink_class in self.SINK_TYPES:
            if sink_class.name.lower() == stream_name.lower():
                return sink_class
            if stream_name.lower() in getattr(sink_class, "available_names", []):
                return sink_class
        return None


# Keep cookiecutter entry-point alias used in pyproject.toml
Targetattentive = TargetAttentive


if __name__ == "__main__":
    TargetAttentive.cli()
