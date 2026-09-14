"""Attentive target sinks for Profiles and Events."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from singer_sdk.exceptions import FatalAPIError

from target_attentive.client import AttentiveSink

_HAS_TZ = re.compile(r"(Z|[+-]\d{2}:?\d{2})$", re.IGNORECASE)

# Hotglue.io Attentive API Sign-up Unit (INTEGRATION). Used when tenant config
# omits ``sign_up_source_id``.
DEFAULT_SIGN_UP_SOURCE_ID = "1446033"


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


def _normalize_occurred_at(value: Any) -> Optional[str]:
    """Coerce timestamps to RFC 3339 with UTC offset (Attentive Custom Events API)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    text = str(value).strip()
    if not text:
        return None
    # Common pandas/Recharge form: "2026-09-10 15:34:36"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    if _HAS_TZ.search(text):
        return text
    # Assume UTC when no offset is present.
    if text.endswith("Z") or text.endswith("z"):
        return text
    return f"{text}Z"


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
    """Upsert custom attributes on an Attentive user (profile).

    By default opts the user into an Attentive subscription first so they appear
    under Subscribers. Uses config ``sign_up_source_id``, falling back to
    ``DEFAULT_SIGN_UP_SOURCE_ID``.
    """

    name = "Profiles"
    available_names = ["profiles", "profile", "customers", "contacts"]
    endpoint = "/attributes/custom"
    subscribe_endpoint = "/subscriptions"

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

    def _subscribe_enabled(self) -> bool:
        # Default on so exported profiles show under Attentive Subscribers.
        return bool(self.config.get("subscribe_profiles", True))

    def _resolve_sign_up_source_id(self) -> str:
        configured = self.config.get("sign_up_source_id")
        if configured is not None and str(configured).strip():
            return str(configured).strip()
        return DEFAULT_SIGN_UP_SOURCE_ID

    def _build_subscribe_payload(self, user: dict) -> dict:
        """Build POST /subscriptions body with signUpSourceId.

        See https://docs.attentive.com/reference/addsubscriptions
        """
        payload: Dict[str, Any] = {
            "user": user,
            "signUpSourceId": self._resolve_sign_up_source_id(),
        }

        subscription_type = self.config.get("subscription_type")
        if subscription_type:
            subscription_type = str(subscription_type).upper()
            if subscription_type not in ("MARKETING", "TRANSACTIONAL"):
                raise FatalAPIError(
                    f"Invalid subscription_type {subscription_type!r}; "
                    "expected MARKETING or TRANSACTIONAL."
                )
            payload["subscriptionType"] = subscription_type

        if self.config.get("single_opt_in"):
            payload["singleOptIn"] = True

        return payload

    def _ensure_subscribed(self, user: dict) -> None:
        """Opt the user in so they show up under Attentive Subscribers."""
        if not self._subscribe_enabled():
            return

        payload = self._build_subscribe_payload(user)
        self.logger.info(
            "Subscribing Attentive user before attributes: %s (signUpSourceId=%s)",
            user.get("email") or user.get("phone"),
            payload.get("signUpSourceId"),
        )
        # Attentive returns 202 Accepted for new subscriptions.
        self.request_api("POST", endpoint=self.subscribe_endpoint, request_data=payload)

    def upsert_record(self, record: dict, context: dict) -> Tuple[Any, bool, dict]:
        state_updates: Dict[str, Any] = {}
        if not record:
            return None, True, {"existing": True}

        user = record.get("user") or {}
        self._ensure_subscribed(user)

        response = self.request_api("POST", request_data=record)
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

        occurred_at = _normalize_occurred_at(record.get("occurredAt"))
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
