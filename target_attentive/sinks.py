"""Attentive target sinks for Profiles and Events."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from target_attentive.client import AttentiveSink


def _scalar_properties(properties: Optional[dict]) -> dict:
    """Drop nulls and non-scalar values (Attentive rejects arrays/maps as values)."""
    if not properties or not isinstance(properties, dict):
        return {}
    cleaned = {}
    for key, value in properties.items():
        if value is None:
            continue
        if isinstance(value, (list, dict)):
            continue
        cleaned[str(key)] = value
    return cleaned


def _build_user(record: dict) -> Optional[dict]:
    user = {}
    email = record.get("email")
    phone = record.get("phone")
    if email:
        user["email"] = email
    if phone:
        user["phone"] = phone
    return user or None


class ProfilesSink(AttentiveSink):
    """Upsert custom attributes on an Attentive user (profile)."""

    name = "Profiles"
    available_names = ["profiles", "profile", "customers", "contacts"]
    endpoint = "/attributes/custom"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        user = _build_user(record)
        if not user:
            self.logger.warning(
                "Skipping Profiles record with no email or phone: %s", record
            )
            return {}

        custom_attributes = record.get("custom_attributes") or record.get("properties") or {}
        properties = _scalar_properties(custom_attributes)
        if not properties:
            self.logger.warning(
                "Skipping Profiles record with no custom attributes: %s", user
            )
            return {}

        return {"user": user, "properties": properties}

    def upsert_record(self, record: dict, context: dict) -> Tuple[Any, bool, dict]:
        state_updates: Dict[str, Any] = {}
        if not record:
            return None, True, {"existing": True}

        response = self.request_api("POST", request_data=record)
        user = record.get("user") or {}
        record_id = user.get("email") or user.get("phone")
        return record_id, response.ok, state_updates


class EventsSink(AttentiveSink):
    """Post custom events to Attentive."""

    name = "Events"
    available_names = ["events", "event"]
    endpoint = "/events/custom"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        event_type = record.get("type")
        user = _build_user(record)
        if not event_type or not user:
            self.logger.warning(
                "Skipping Events record missing type or user identity: %s", record
            )
            return {}

        payload: Dict[str, Any] = {
            "type": event_type,
            "user": user,
        }

        properties = _scalar_properties(record.get("properties"))
        if properties:
            payload["properties"] = properties

        external_event_id = record.get("externalEventId")
        if external_event_id:
            payload["externalEventId"] = str(external_event_id)

        occurred_at = record.get("occurredAt")
        if occurred_at:
            payload["occurredAt"] = occurred_at

        return payload

    def upsert_record(self, record: dict, context: dict) -> Tuple[Any, bool, dict]:
        state_updates: Dict[str, Any] = {}
        if not record:
            return None, True, {"existing": True}

        response = self.request_api("POST", request_data=record)
        record_id = record.get("externalEventId") or record.get("type")
        return record_id, response.ok, state_updates
