"""Pydantic models: the contract between the model build and the web app.

Every entity model is registered with @entity("<type>") so build.py can
validate entities and export one JSON Schema per type.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

ENTITY_MODELS: dict[str, type["Strict"]] = {}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def entity(type_name: str):
    def register(cls: type[Strict]) -> type[Strict]:
        ENTITY_MODELS[type_name] = cls
        return cls
    return register


# ---- Shared shapes ---------------------------------------------------------

class Link(Strict):
    type: str
    key: str
    name: str | None
    missing: bool


class EffectApplication(Strict):
    effect: Link
    scope: str | None
    value: float
    source: Link
    value_damaged: float | None = None      # buildings only
    value_ruined: float | None = None       # buildings only
    context_requirement: str | None = None  # buildings only
    advancement_stage: str | None = None    # effect bundles only


# ---- Effects ---------------------------------------------------------------

class BonusTarget(Strict):
    bonus_value_id: str
    source_table: str
    target_table: str | None
    target_key: str | None
    target: Link | None
    unit_set: str | None
    ability: Link | None
    attribute: str | None
    phase: str | None


@entity("effect")
class Effect(Strict):
    key: str
    description: str | None
    additional_tooltip: str | None
    category: str
    icon: str | None
    icon_negative: str | None
    priority: int
    is_positive_value_good: bool
    bonus_targets: list[BonusTarget]
    sources: list[Link] = []


@entity("effect_bundle")
class EffectBundle(Strict):
    key: str
    title: str | None
    description: str | None
    target: str
    priority: int
    icon: str | None
    is_global_effect: bool
    effects: list[EffectApplication]


# ---- Abilities -------------------------------------------------------------

class Activation(Strict):
    passive: bool
    active_time: float
    recharge_time: float
    initial_recharge: float
    num_uses: int
    effect_range: float
    min_range: float
    mana_cost: float
    wind_up_time: float
    miscast_chance: float
    target_self: bool
    target_friends: bool
    target_enemies: bool
    target_ground: bool
    affect_self: bool
    num_effected_friendly_units: int
    num_effected_enemy_units: int
    spawned_unit: str | None
    activated_projectile: str | None
    bombardment: str | None
    vortex: str | None


class StatEffect(Strict):
    stat: str
    stat_name: str | None
    value: float
    how: str


class AttributeEffect(Strict):
    attribute: str
    attribute_type: str


class Phase(Strict):
    key: str
    order: int
    target_self: bool
    target_friends: bool
    target_enemies: bool
    duration: float
    effect_type: str
    stat_effects: list[StatEffect]
    attribute_effects: list[AttributeEffect]
    damage_amount: int
    max_damaged_entities: int
    heal_amount: float
    hp_change_frequency: float
    resurrect: bool
    imbue_magical: bool
    imbue_ignition: int
    replenish_ammo: float
    fatigue_change_ratio: float
    ability_recharge_change: float
    mana_regen_mod: float
    cant_move: bool
    execute_ratio: float
    is_hidden_in_ui: bool


@entity("ability")
class Ability(Strict):
    key: str
    name: str | None
    description: str | None
    type: str
    type_name: str | None
    source_type: str
    source_type_name: str | None
    icon: str
    is_hidden_in_ui: bool
    is_unit_upgrade: bool
    requires_effect_enabling: bool
    activation: Activation | None
    phases: list[Phase]
    units: list[Link] = []
    characters: list[Link] = []
    modified_by_effects: list[Link] = []
