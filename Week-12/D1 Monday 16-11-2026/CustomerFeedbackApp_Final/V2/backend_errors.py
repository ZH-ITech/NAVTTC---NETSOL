"""Shared exception for optional sentiment backends (DistilBERT now, Azure later)."""


class BackendUnavailable(RuntimeError):
    """The requested backend cannot be used right now; the caller falls back to VADER."""
