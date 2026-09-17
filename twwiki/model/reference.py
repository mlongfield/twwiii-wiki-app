"""Reference documents written next to the entities: campaigns, UI colours and UI labels."""

from __future__ import annotations

import colorsys

from pydantic import TypeAdapter

from .context import Context, grouped, opt
from .schemas import CampaignSummary, Colour

COLOUR_PROFILES = ("deuteranopia", "protanopia", "tritanopia")
DARK_MIN_LIGHTNESS = 0.6

# Label name -> uied_component_texts loc key for game UI labels the web app shows.
UI_LABEL_KEYS = {
    "abilities": "uied_component_texts_localised_string_tab_title_active_Text_1f005b",
    "cooldown": "uied_component_texts_localised_string_ComponentText_9180a7ac",
    "duration": "uied_component_texts_localised_string_tx_duration_default_Text_130017",
    "effects": "uied_component_texts_localised_string_tx_effects_NewState_Text_770033",
    "range": "uied_component_texts_localised_string_range_NewState_Text_60059",
    "research_rate": "uied_component_texts_localised_string_label_research_rate_NewState_Text_60007",
    "stats": "uied_component_texts_localised_string_dy_title_NewState_Text_41",
    "uses": "uied_component_texts_localised_string_tx_charges_default_Text_20000a",
}

REFERENCE_TYPES: dict[str, TypeAdapter] = {
    "campaigns": TypeAdapter(list[CampaignSummary]),
    "colours": TypeAdapter(list[Colour]),
    "ui_labels": TypeAdapter(dict[str, str | None]),
}


def hex_colour(value) -> str | None:
    value = opt(value)
    return f"#{value.upper()}" if value else None


def dark_hex(hex_value: str) -> str:
    """The colour for a dark background: lightness raised to 60% when the colour reads as dark
    (its brightest channel is below 60%), same hue and saturation."""
    r, g, b = (int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    if max(r, g, b) >= DARK_MIN_LIGHTNESS:
        return hex_value
    h, _lightness, s = colorsys.rgb_to_hls(r, g, b)
    return "#" + "".join(f"{round(c * 255):02X}" for c in colorsys.hls_to_rgb(h, DARK_MIN_LIGHTNESS, s))


def campaigns_doc(entities: dict[str, list[dict]]) -> list[dict]:
    return [{"key": c["key"], "name": c["name"], "map": c["map"],
             "playable_factions": len(c["playable_factions"]), "major_factions": len(c["major_factions"])}
            for c in entities.get("campaign", [])]


def colours_doc(ctx: Context) -> list[dict]:
    if not ctx.table_exists("ui_colours"):
        return []
    overrides = grouped(ctx, "ui_colour_profile_colour_overrides", "colour", "colour_profile")
    out = []
    for r in ctx.rows('SELECT key, description, "unnamed colour group_1" AS hex FROM ui_colours ORDER BY key'):
        value = hex_colour(r["hex"])
        if value is None:
            continue
        profiles = {o["colour_profile"]: hex_colour(o["colour_hex"]) for o in overrides.get(r["key"], [])}
        out.append({"key": r["key"], "description": r["description"] or "", "hex": value, "dark_hex": dark_hex(value),
                    "profiles": {p: profiles.get(p) for p in COLOUR_PROFILES}})
    return out


def ui_labels_doc(ctx: Context) -> dict[str, str | None]:
    labels: dict[str, str | None] = {}
    for name, key in sorted(UI_LABEL_KEYS.items()):
        text = ctx.loc.text(key)
        text = text.strip().rstrip(":").strip() if text else ""
        if not text:
            ctx.tally["ui_labels_without_text"] += 1
        labels[name] = text or None
    return labels


def build_reference(ctx: Context, entities: dict[str, list[dict]]) -> dict[str, list | dict]:
    docs = {"campaigns": campaigns_doc(entities), "colours": colours_doc(ctx), "ui_labels": ui_labels_doc(ctx)}
    return {name: REFERENCE_TYPES[name].dump_python(REFERENCE_TYPES[name].validate_python(doc), mode="json")
            for name, doc in docs.items()}
