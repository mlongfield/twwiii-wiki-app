from pathlib import Path

import tests.model.test_abilities as t_abilities
import tests.model.test_buildings as t_buildings
import tests.model.test_characters as t_characters
import tests.model.test_effects as t_effects
import tests.model.test_factions as t_factions
import tests.model.test_items as t_items
import tests.model.test_technologies as t_technologies
import tests.model.test_units as t_units
from twwiki.model import abilities, buildings, characters, effects, factions, items, schemas, technologies, units
from twwiki.model.images import ImageIndex


def with_images(ctx, *paths):
    ctx.images = ImageIndex(Path("images"), paths)
    return ctx


def test_ability_icon_image():
    ctx = with_images(t_abilities.ability_context(), "ui/battle ui/ability_icons/hold.png")
    built = {a["key"]: a for a in abilities.build(ctx)["ability"]}
    assert built["hold"]["icon_image"] == "ui/battle ui/ability_icons/hold.png"
    assert built["plain"]["icon_image"] is None
    assert ctx.images.stats["ability.icon_image"]["missing"] == 1
    for a in built.values():
        schemas.ENTITY_MODELS["ability"].model_validate(a)


def test_skill_icon_image_uses_folder_then_unique_file_name():
    ctx = with_images(t_characters.character_context(),
                      "ui/campaign ui/skills/leader.png", "ui/campaign ui/skills/sub/mentor.png")
    built = {s["key"]: s for s in characters.build(ctx)["skill"]}
    assert built["leader_of_men"]["icon_image"] == "ui/campaign ui/skills/leader.png"
    assert built["mentor"]["icon_image"] == "ui/campaign ui/skills/sub/mentor.png"
    for s in built.values():
        schemas.ENTITY_MODELS["skill"].model_validate(s)


def test_technology_icon_image():
    ctx = with_images(t_technologies.tech_context(), "ui/campaign ui/technologies/hw.png")
    built = {t["key"]: t for t in technologies.build(ctx)["technology"]}
    assert built["heavy_weapons"]["icon_image"] == "ui/campaign ui/technologies/hw.png"
    assert built["piracy"]["icon_image"] is None
    for t in built.values():
        schemas.ENTITY_MODELS["technology"].model_validate(t)


def test_effect_and_bundle_icon_images():
    ctx = with_images(t_effects.effects_context(),
                      "ui/campaign ui/effect_bundles/a.png", "ui/campaign ui/effect_bundles/b.png")
    built = effects.build(ctx)
    by_key = {e["key"]: e for e in built["effect"]}
    assert by_key["e_attack"]["icon_image"] == "ui/campaign ui/effect_bundles/a.png"
    assert by_key["e_attack"]["icon_negative_image"] is None
    assert by_key["e_research"]["icon_image"] is None
    assert "effect.icon_negative_image" not in ctx.images.stats
    assert built["effect_bundle"][0]["icon_image"] == "ui/campaign ui/effect_bundles/b.png"
    for e in built["effect"]:
        schemas.ENTITY_MODELS["effect"].model_validate(e)
    schemas.ENTITY_MODELS["effect_bundle"].model_validate(built["effect_bundle"][0])


def test_trait_icon_image_comes_from_its_category():
    ctx = with_images(t_items.items_context(), "ui/campaign ui/skills/trait_personality.png")
    ctx.con.execute("CREATE TABLE trait_categories (category VARCHAR, icon_path VARCHAR)")
    ctx.con.execute("INSERT INTO trait_categories VALUES (?, ?)",
                    ["personality", "ui\\campaign ui\\skills\\trait_personality.png"])
    built = {t["key"]: t for t in items.build(ctx)["trait"]}
    assert built["brave"]["icon_image"] == "ui/campaign ui/skills/trait_personality.png"
    for t in built.values():
        schemas.ENTITY_MODELS["trait"].model_validate(t)


def test_unit_card_uses_the_default_variant_and_portrait_the_first_by_faction():
    ctx = with_images(t_units.unit_context({
        "unit_variants": [
            {"faction": "", "name": "", "unit": "gs_land", "variant": "", "unit_card": "gs_card"},
            {"faction": "reikland", "name": "", "unit": "arch_land", "variant": "", "unit_card": "reik_archers"},
        ],
        "units_custom_battle_permissions": [
            {"faction": "reikland", "unit": "gs", "general_portrait": ""},
            {"faction": "reikland", "unit": "archers",
             "general_portrait": "ui\\portraits\\portholes\\no_culture\\reik_captain_0.png"},
            {"faction": "averland", "unit": "archers",
             "general_portrait": "ui/portraits/portholes/no_culture/aver_captain_0.png"},
        ],
    }), "ui/units/icons/gs_card.png", "ui/units/icons/reik_archers.png",
        "ui/portraits/portholes/no_culture/reik_captain_0.png", "ui/portraits/portholes/no_culture/aver_captain_0.png")
    built = {u["key"]: u for u in units.build(ctx)["unit"]}
    assert built["gs"]["card_image"] == "ui/units/icons/gs_card.png"
    assert built["gs"]["portrait_image"] is None
    assert built["archers"]["card_image"] is None
    assert built["archers"]["portrait_image"] == "ui/portraits/portholes/no_culture/aver_captain_0.png"
    assert built["ship"]["card_image"] is None and built["ship"]["portrait_image"] is None
    for u in built.values():
        schemas.ENTITY_MODELS["unit"].model_validate(u)


def test_item_icon_image_comes_from_its_type():
    ctx = with_images(t_items.items_context(), "ui/campaign ui/ancillaries/arcane_item.png")
    ctx.con.execute("CREATE TABLE ancillary_types (type VARCHAR, ui_icon VARCHAR)")
    ctx.con.execute("INSERT INTO ancillary_types VALUES (?, ?)",
                    ["wh_main_anc_arcane_item", "ui/campaign ui/ancillaries/arcane_item.png"])
    built = {i["key"]: i for i in items.build(ctx)["item"]}
    assert built["blue_khepra"]["icon_image"] == "ui/campaign ui/ancillaries/arcane_item.png"
    for i in built.values():
        schemas.ENTITY_MODELS["item"].model_validate(i)


def test_faction_flag_image():
    ctx = with_images(t_factions.factions_context(), "ui/flags/reikland/mon_64.png")
    faction = factions.build(ctx)["faction"][0]
    assert faction["flag_image"] == "ui/flags/reikland/mon_64.png"
    schemas.ENTITY_MODELS["faction"].model_validate(faction)


def test_building_level_icon_image_uses_the_naming_variant():
    ctx = with_images(t_buildings.building_context(), "ui/buildings/icons/emp_barracks.png",
                      "ui/buildings/icons/black_tower.png", "ui/buildings/icons/faction_tower.png")
    ctx.con.execute("""UPDATE building_culture_variants SET icon = CASE
        WHEN building = 'barracks_1' THEN 'emp_barracks'
        WHEN faction = 'followers' THEN 'faction_tower'
        ELSE 'black_tower' END""")
    built = {b["key"]: b for b in buildings.build(ctx)["building_level"]}
    assert built["barracks_1"]["icon_image"] == "ui/buildings/icons/emp_barracks.png"
    assert built["tower"]["icon_image"] == "ui/buildings/icons/black_tower.png"
    assert built["barracks_2"]["icon_image"] is None
    assert ctx.images.stats["building_level.icon_image"]["referenced"] == 2
    for b in built.values():
        schemas.ENTITY_MODELS["building_level"].model_validate(b)
