"""Authoritative mapping from TEP friendly sensor names to their canonical
XMEAS_/XMV_ tag identifiers.

Used by the agent tools so that whenever the agent surfaces a sensor or a
manipulated variable in its reasoning, it can name the exact instrument tag
that an operator would see on the DCS (e.g. `XMV_3 (A feed load)`). Without
this, the LLM has only friendly names and hedges its answers.

Source of truth: `backend/tep_faultexplainer_bridge.py` — kept in sync with
that file by hand. If you add or rename a sensor there, mirror it here.
"""

from __future__ import annotations

from typing import Dict, Optional


# XMEAS = process measurements (read-only sensors), 41 in total.
XMEAS_TAGS: Dict[str, str] = {
    "A Feed": "XMEAS_1",
    "D Feed": "XMEAS_2",
    "E Feed": "XMEAS_3",
    "A and C Feed": "XMEAS_4",
    "Recycle Flow": "XMEAS_5",
    "Reactor Feed Rate": "XMEAS_6",
    "Reactor Pressure": "XMEAS_7",
    "Reactor Level": "XMEAS_8",
    "Reactor Temperature": "XMEAS_9",
    "Purge Rate": "XMEAS_10",
    "Product Sep Temp": "XMEAS_11",
    "Product Sep Level": "XMEAS_12",
    "Product Sep Pressure": "XMEAS_13",
    "Product Sep Underflow": "XMEAS_14",
    "Stripper Level": "XMEAS_15",
    "Stripper Pressure": "XMEAS_16",
    "Stripper Underflow": "XMEAS_17",
    "Stripper Temp": "XMEAS_18",
    "Stripper Steam Flow": "XMEAS_19",
    "Compressor Work": "XMEAS_20",
    "Reactor Coolant Temp": "XMEAS_21",
    "Separator Coolant Temp": "XMEAS_22",
    "Component A to Reactor": "XMEAS_23",
    "Component B to Reactor": "XMEAS_24",
    "Component C to Reactor": "XMEAS_25",
    "Component D to Reactor": "XMEAS_26",
    "Component E to Reactor": "XMEAS_27",
    "Component F to Reactor": "XMEAS_28",
    "Component A in Purge": "XMEAS_29",
    "Component B in Purge": "XMEAS_30",
    "Component C in Purge": "XMEAS_31",
    "Component D in Purge": "XMEAS_32",
    "Component E in Purge": "XMEAS_33",
    "Component F in Purge": "XMEAS_34",
    "Component G in Purge": "XMEAS_35",
    "Component H in Purge": "XMEAS_36",
    "Component D in Product": "XMEAS_37",
    "Component E in Product": "XMEAS_38",
    "Component F in Product": "XMEAS_39",
    "Component G in Product": "XMEAS_40",
    "Component H in Product": "XMEAS_41",
}

# XMV = manipulated variables (valves / setpoints the controller drives), 11 total.
XMV_TAGS: Dict[str, str] = {
    "D feed load": "XMV_1",
    "E feed load": "XMV_2",
    "A feed load": "XMV_3",
    "A and C feed load": "XMV_4",
    "Compressor recycle valve": "XMV_5",
    "Purge valve": "XMV_6",
    "Separator liquid load": "XMV_7",
    "Stripper liquid load": "XMV_8",
    "Stripper steam valve": "XMV_9",
    "Reactor coolant load": "XMV_10",
    "Condenser coolant load": "XMV_11",
}

# Combined lookup. Case-insensitive helper below.
_ALL_TAGS: Dict[str, str] = {**XMEAS_TAGS, **XMV_TAGS}
_ALL_TAGS_LOWER: Dict[str, str] = {k.lower(): v for k, v in _ALL_TAGS.items()}


def tag_for(friendly_name: str) -> Optional[str]:
    """Return the XMEAS_X / XMV_Y tag for a friendly sensor name, or None."""
    if not friendly_name:
        return None
    return _ALL_TAGS.get(friendly_name) or _ALL_TAGS_LOWER.get(friendly_name.lower())


def label_with_tag(friendly_name: str) -> str:
    """`'A feed load' -> 'XMV_3 (A feed load)'`. Falls back to the name if unknown."""
    tag = tag_for(friendly_name)
    return f"{tag} ({friendly_name})" if tag else friendly_name


def is_manipulated(friendly_name: str) -> bool:
    """True for XMV_* (valves and setpoints), False for XMEAS_* and unknown."""
    tag = tag_for(friendly_name)
    return tag is not None and tag.startswith("XMV_")
