"""Helpers for working with farmer profiles."""


def profile_summary(farmer: dict | None) -> dict | None:
    """Return the fields the AI prompt cares about (None-safe)."""
    if not farmer:
        return None
    return {
        "name": farmer.get("name", "Unknown"),
        "location": farmer.get("location", "Ghana"),
        "primary_crop": farmer.get("primary_crop", "Unknown"),
        "farm_size": farmer.get("farm_size", "Unknown"),
        "language": farmer.get("language", "English"),
    }