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


# ---- Characters and skills -------------------------------------------------

class LoreOfMagic(Strict):
    key: str
    name: str | None


class SkillTreeNode(Strict):
    key: str
    skill: Link
    tier: int
    indent: int
    points_on_creation: int
    required_num_parents: int
    visible_in_ui: bool
    faction: str | None
    subculture: str | None
    campaign: str | None


class SkillTreeLink(Strict):
    parent: str
    child: str
    link_type: str
    initial_descent_tiers: int


class SkillLock(Strict):
    node: str
    skill: Link
    level: int


class SkillTree(Strict):
    key: str
    agent_type: str | None
    faction: str | None
    subculture: str | None
    campaign: str | None
    for_army: bool
    for_navy: bool
    nodes: list[SkillTreeNode]
    links: list[SkillTreeLink]
    locks: list[SkillLock]


class SkillLevel(Strict):
    level: int
    unlocked_at_rank: int | None
    effects: list[EffectApplication]


@entity("character")
class Character(Strict):
    key: str
    name: str | None
    title: str | None
    description: str | None
    agent_types: list[str]
    associated_unit: Link | None
    lore_of_magic: LoreOfMagic | None
    is_caster: bool
    can_equip_ancillaries: bool
    recruitable: bool
    can_gain_xp: bool
    cost: int
    cap: int
    factions: list[Link]
    abilities: list[Link]
    skill_trees: list[SkillTree]
    items: list[Link] = []


@entity("skill")
class Skill(Strict):
    key: str
    name: str | None
    description: str | None
    image: str
    unlocked_at_rank: int
    is_background_skill: bool
    levels: list[SkillLevel]
    characters: list[Link] = []


# ---- Technologies ----------------------------------------------------------

class PooledResourceCost(Strict):
    pooled_resource_factor: str
    amount: int
    context: str


class ResourceCost(Strict):
    key: str
    treasury_cost: int
    pooled_resources: list[PooledResourceCost]
    trade_resources: list[str]


class Placement(Strict):
    tree: Link
    node_key: str
    tier: int
    indent: int
    research_points_required: int
    cost_per_round: int
    resource_cost: ResourceCost | None


class TreeNode(Strict):
    key: str
    technology: Link
    tier: int
    indent: int
    research_points_required: int
    cost_per_round: int
    resource_cost: ResourceCost | None
    required_parents: int
    ui_group: str | None
    pixel_offset_x: int
    pixel_offset_y: int


class TreeLink(Strict):
    parent: str
    child: str
    initial_descent_tiers: int
    visible_in_ui: bool


@entity("technology")
class Technology(Strict):
    key: str
    name: str | None
    description: str | None
    long_description: str | None
    icon: str
    is_civil: bool
    is_engineering: bool
    is_military: bool
    is_hidden: bool
    unlocked_by_building: Link | None
    required_technologies: list[Link]
    required_buildings: list[Link]
    effects: list[EffectApplication]
    placements: list[Placement]


@entity("technology_tree")
class TechnologyTree(Strict):
    key: str
    name: str | None
    culture: Link | None
    subculture: Link | None
    faction: Link | None
    campaign: str | None
    colour: str | None
    nodes: list[TreeNode]
    links: list[TreeLink]


# ---- Buildings -------------------------------------------------------------

@entity("building_level")
class BuildingLevel(Strict):
    key: str
    name: str | None
    short_description: str | None
    chain: Link | None
    level: int
    create_time: int
    create_cost: int
    upkeep_cost: int
    development_point_cost: int
    food_cost: int
    only_in_capital: bool
    faction_unique: bool
    can_convert: bool
    visible_in_ui: bool
    resource_cost: ResourceCost | None
    cultures: list[str]
    effects: list[EffectApplication]
    units_recruited: list[Link]


@entity("building_chain")
class BuildingChain(Strict):
    key: str
    name: str | None
    category: str | None
    in_encyclopedia: bool
    levels: list[Link]


# ---- Items and traits ------------------------------------------------------

class RequiredSkill(Strict):
    skill: Link
    level: int


@entity("item")
class Item(Strict):
    key: str
    name: str | None
    description: str | None
    explanation: str | None
    type: str
    category: str
    subcategory: str | None
    legendary: bool
    applies_to: str
    transferrable: bool
    unique_to_world: bool
    unique_to_faction: bool
    bodyguard_unit: Link | None
    agent_types: list[str]
    agent_subtypes: list[Link]
    required_skills: list[RequiredSkill]
    effects: list[EffectApplication]


class TraitLevel(Strict):
    key: str
    level: int
    name: str | None
    description: str | None
    threshold_points: int
    effects: list[EffectApplication]


@entity("trait")
class Trait(Strict):
    key: str
    name: str | None
    hidden: bool
    precedence: int
    icon: str
    no_going_back_level: int
    levels: list[TraitLevel]
    antitraits: list[Link]
