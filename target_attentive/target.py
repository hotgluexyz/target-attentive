"""attentive target class."""

from __future__ import annotations

from singer_sdk import typing as th
from singer_sdk.target_base import Target
from target_hotglue.target import TargetHotglue

from target_attentive.sinks import (
    attentiveSink,
)


class Targetattentive(Target, TargetHotglue):
    """Sample target for attentive."""

    name = "target-attentive"

    SINK_TYPES = []
    MAX_PARALLELISM = 1

    def get_sink_class(self, stream_name: str):
        return attentiveSink


if __name__ == "__main__":
    Targetattentive.cli()
