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


# ---- Units -----------------------------------------------------------------

class BaseStats(Strict):
    num_men: int
    hit_points_per_entity: int | None
    bonus_hit_points: int
    walk_speed: float | None
    run_speed: float | None
    charge_speed: float | None
    fly_speed: float | None
    mass: float | None
    melee_attack: int
    melee_defence: int
    charge_bonus: int
    morale: int
    accuracy: int
    reload: int
    armour: int | None
    primary_ammo: int
    secondary_ammo: int
    damage_mod_physical: int
    damage_mod_magic: int
    damage_mod_flame: int
    damage_mod_missile: int
    damage_mod_all: int
    healing_power: float
    spell_mastery: float
    num_mounts: int
    rank_depth: int


class MeleeWeapon(Strict):
    key: str
    damage: int
    ap_damage: int
    bonus_v_large: int
    bonus_v_infantry: int
    is_magical: bool
    splash_attack_target_size: str | None
    splash_attack_max_attacks: int
    splash_attack_power_multiplier: float
    melee_attack_interval: float
    building_damage_multiplier: float
    ignition_amount: float


class Projectile(Strict):
    key: str
    category: str
    damage: int
    ap_damage: int
    bonus_v_large: int
    bonus_v_infantry: int
    effective_range: int
    minimum_range: int
    base_reload_time: float
    projectile_number: int
    shots_per_volley: int
    burst_size: int
    marksmanship_bonus: float
    is_magical: bool
    ignition_amount: float
    shockwave_radius: float
    explosion_type: str | None


class MissileWeapon(Strict):
    key: str
    projectile: Projectile | None


class Shield(Strict):
    key: str
    shield_defence_value: int
    shield_armour_value: int
    missile_block_chance: int


class UnitAttribute(Strict):
    key: str
    name: str | None
    description: str | None


class UnitSetMembership(Strict):
    key: str
    conditional: bool
    min_exp_level: int | None
    max_exp_level: int | None


@entity("unit")
class Unit(Strict):
    key: str
    name: str | None
    short_description: str | None
    caste: str
    caste_name: str | None
    category: str | None
    category_name: str | None
    unit_class: str | None
    class_name: str | None
    is_naval: bool
    tier: int
    land_unit: str | None
    recruitment_cost: int
    upkeep_cost: int
    multiplayer_cost: int
    campaign_cap: int
    multiplayer_cap: int
    base_stats: BaseStats | None
    melee_weapon: MeleeWeapon | None
    missile_weapon: MissileWeapon | None
    shield: Shield | None
    mount: str | None
    attributes: list[UnitAttribute]
    abilities: list[Link]
    characters: list[Link]
    unit_sets: list[UnitSetMembership]
    custom_battle_factions: list[Link]
    recruited_by_buildings: list[Link]
