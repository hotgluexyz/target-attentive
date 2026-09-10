"""Attentive API authentication helpers."""

from target_hotglue.auth import ApiAuthenticator


def get_attentive_authenticator(target, state=None):
    """Return a Bearer-token authenticator using config ``api_key``."""
    return ApiAuthenticator(
        target,
        state=state or {},
        header_name="Authorization",
        header_value_prefix="Bearer ",
        config_key="api_key",
    )
