"""Exceptions for Cloudflare Advanced integration."""

from __future__ import annotations


class CloudflareError(Exception):
    """Base exception for Cloudflare Advanced integration."""


class CloudflareAuthError(CloudflareError):
    """Exception raised for authentication errors."""


class CloudflareApiError(CloudflareError):
    """Exception raised for API level errors."""


class CloudflareConnectionError(CloudflareError):
    """Exception raised for network connection errors."""
