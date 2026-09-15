"""Unit abilities: activation parameters and ordered phases."""

from __future__ import annotations

from .context import Context, by_key, grouped, opt
from .images import ABILITY_ICONS

ACTIVATION_FIELDS = (
    "passive", "active_time", "recharge_time", "initial_recharge", "num_uses", "effect_range",
    "min_range", "mana_cost", "wind_up_time", "miscast_chance", "target_self", "target_friends",
    "target_enemies", "target_ground", "affect_self", "num_effected_friendly_units",
    "num_effected_enemy_units",
)
ACTIVATION_KEYS = ("spawned_unit", "activated_projectile", "bombardment", "vortex")
PHASE_FIELDS = (
    "duration", "effect_type", "damage_amount", "max_damaged_entities", "heal_amount",
    "hp_change_frequency", "resurrect", "imbue_magical", "imbue_ignition", "replenish_ammo",
    "fatigue_change_ratio", "ability_recharge_change", "mana_regen_mod", "cant_move",
    "execute_ratio", "is_hidden_in_ui",
)


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    names: dict[str, str | None] = {}
    if ctx.table_exists("unit_abilities"):
        for r in ctx.rows("SELECT key FROM unit_abilities"):
            names[r["key"]] = ctx.catalog_name("ability", f"unit_abilities_onscreen_name_{r['key']}")
    return {"ability": names}


def build(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("ability", "unit_abilities"):
        return {"ability": []}
    special = by_key(ctx, "unit_special_abilities", "key")
    phase_links = grouped(ctx, "special_ability_to_special_ability_phase_junctions",
                          "special_ability", '"order", phase')
    phases = by_key(ctx, "special_ability_phases", "id")
    stat_effects = grouped(ctx, "special_ability_phase_stat_effects", "phase", "stat")
    attribute_effects = grouped(ctx, "special_ability_phase_attribute_effects", "phase", "attribute")
    stat_loc = {k: v["localisation"] for k, v in by_key(ctx, "modifiable_unit_stats", "stat_key").items()}

    out = []
    for r in ctx.rows("SELECT * FROM unit_abilities ORDER BY key"):
        key = r["key"]
        built_phases = []
        for link in phase_links.get(key, []):
            phase = phases.get(link["phase"])
            if phase is None:
                ctx.links.missing["ability.phase->special_ability_phase"] += 1
                continue
            built_phases.append(_phase(ctx, link, phase, stat_effects, attribute_effects, stat_loc))
        out.append({
            "key": key,
            "name": ctx.links.name("ability", key),
            "description": ctx.loc.text(f"unit_abilities_tooltip_text_{key}"),
            "type": r["type"],
            "type_name": ctx.loc.text(f"unit_ability_types_onscreen_name_{r['type']}"),
            "source_type": r["source_type"],
            "source_type_name": ctx.loc.text(f"unit_ability_source_types_name_{r['source_type']}"),
            "icon": r["icon_name"],
            "icon_image": ctx.images.resolve("ability.icon_image", r["icon_name"], ABILITY_ICONS),
            "is_hidden_in_ui": r["is_hidden_in_ui"],
            "is_unit_upgrade": r["is_unit_upgrade"],
            "requires_effect_enabling": r["requires_effect_enabling"],
            "activation": _activation(special.get(key)),
            "phases": built_phases,
            "units": [],
            "characters": [],
            "modified_by_effects": [],
        })
    return {"ability": out}


def _activation(row: dict | None) -> dict | None:
    if row is None:
        return None
    activation = {f: row[f] for f in ACTIVATION_FIELDS}
    activation.update({f: opt(row[f]) for f in ACTIVATION_KEYS})
    return activation


def _phase(ctx: Context, link: dict, phase: dict, stat_effects: dict, attribute_effects: dict,
           stat_loc: dict) -> dict:
    stat_effects_list = []
    for s in stat_effects.get(phase["id"], []):
        stat = s["stat"]
        if stat not in stat_loc:
            ctx.links.missing["ability.stat->modifiable_unit_stat"] += 1
            stat_name = None
        else:
            stat_name = ctx.loc.text(f"unit_stat_localisations_onscreen_name_{stat_loc[stat]}")
        stat_effects_list.append({"stat": stat, "stat_name": stat_name, "value": s["value"], "how": s["how"]})

    built = {
        "key": phase["id"],
        "order": link["order"],
        "target_self": link["target_self"],
        "target_friends": link["target_friends"],
        "target_enemies": link["target_enemies"],
        "stat_effects": stat_effects_list,
        "attribute_effects": [
            {"attribute": a["attribute"], "attribute_type": a["attribute_type"]}
            for a in attribute_effects.get(phase["id"], [])
        ],
    }
    built.update({f: phase[f] for f in PHASE_FIELDS})
    return built
