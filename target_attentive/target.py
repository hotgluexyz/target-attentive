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
        th.Property(
            "subscribe_profiles",
            th.BooleanType,
            default=True,
            description=(
                "If true (default), opt Profiles into an Attentive subscription before "
                "writing custom attributes so they appear under Subscribers. "
                "Requires subscriptions:write scope."
            ),
        ),
        th.Property(
            "sign_up_source_id",
            th.StringType,
            description=(
                "Attentive API Sign-up Unit ID (Sign-up Units tab → ID column). "
                "Falls back to the hardcoded Hotglue demo unit (1446033) when omitted."
            ),
        ),
        th.Property(
            "subscription_type",
            th.StringType,
            description="Optional MARKETING or TRANSACTIONAL passed with subscribe requests.",
        ),
        th.Property(
            "single_opt_in",
            th.BooleanType,
            default=False,
            description=(
                "If true, skip the Reply-Y SMS confirmation when subscribing. "
                "Must be approved by Attentive for the account; otherwise the API returns 400."
            ),
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
