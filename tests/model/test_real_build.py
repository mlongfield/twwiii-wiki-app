"""Known entities and whole-build checks against the real twwiki.duckdb.

Expected values were verified against build fb20553df5af. After a game patch
some may change legitimately; update them deliberately, never to make a
failing build pass unexamined.
"""

import json
from pathlib import Path

import pytest

from twwiki.model.build import build_all
from twwiki.model.context import Context
from twwiki.model.images import ImageIndex
from twwiki.model.schemas import ENTITY_MODELS

DB = Path("twwiki.duckdb")
BASELINE = Path(__file__).parent / "missing_links_baseline.json"
RAW = Path("raw")
IMAGES_BASELINE = Path(__file__).parent / "missing_images_baseline.json"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="twwiki.duckdb not found; run extract and load first")

EXPECTED_COUNTS = {
    "unit": 2609, "character": 613, "skill": 5944, "ability": 2899, "effect": 15064,
    "effect_bundle": 5855, "building_level": 5259, "building_chain": 1943, "technology": 1869,
    "technology_tree": 33, "item": 2671, "trait": 744, "faction": 717, "culture": 27,
    "subculture": 32, "difficulty_level": 7, "campaign_variable": 1052,
    "region": 945, "province": 316,
}


@pytest.fixture(scope="module")
def model():
    ctx = Context.open(DB)
    build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
    ctx.images = ImageIndex.scan(RAW / build_id / "images")
    entities = build_all(ctx)
    yield ctx, {t: {e["key"]: e for e in rows} for t, rows in entities.items()}
    ctx.con.close()


def require_images(ctx):
    if not ctx.images.available:
        pytest.skip("no raw images for this build; run extract with images.folders configured")


def test_every_entity_type_is_built_with_expected_counts(model):
    _, by_type = model
    assert set(by_type) == set(ENTITY_MODELS)
    assert {t: len(rows) for t, rows in by_type.items()} == EXPECTED_COUNTS


def test_greatswords(model):
    gs = model[1]["unit"]["wh_main_emp_inf_greatswords"]
    stats = gs["base_stats"]
    assert gs["name"] == "Greatswords"
    assert (stats["num_men"], stats["hit_points_per_entity"], stats["bonus_hit_points"]) == (120, 8, 68)
    assert (stats["melee_attack"], stats["melee_defence"], stats["armour"]) == (32, 30, 95)
    assert gs["melee_weapon"]["key"] == "wh_main_emp_greatsword"
    assert (gs["melee_weapon"]["damage"], gs["melee_weapon"]["ap_damage"]) == (10, 25)


def test_karl_franz(model):
    by_type = model[1]
    kf = by_type["character"]["wh_main_emp_karl_franz"]
    assert kf["name"] == "Emperor Karl Franz" and kf["title"] == "Legendary Lord"
    assert [t["key"] for t in kf["skill_trees"]] == ["wh_main_skill_node_set_emp_karl_franz"]
    nodes = kf["skill_trees"][0]["nodes"]
    assert len(nodes) == 51
    leader = next(by_type["skill"][n["skill"]["key"]] for n in nodes if n["skill"]["name"] == "Leader of Men")
    aura = [e for e in leader["levels"][0]["effects"] if e["value"] == 50.0]
    assert aura and aura[0]["effect"]["name"].startswith("Leadership aura size")


def test_hold_the_line(model):
    hold = model[1]["ability"]["wh_main_lord_passive_hold_the_line"]
    assert hold["activation"]["passive"] is True and hold["activation"]["effect_range"] == 35.0
    stats = {(s["stat"], s["value"], s["how"]) for p in hold["phases"] for s in p["stat_effects"]}
    assert {("stat_melee_defence", 5.0, "add"), ("stat_morale", 4.0, "add")} <= stats
    assert len(hold["units"]) == 18


def test_training_field(model):
    tf = model[1]["building_level"]["wh_main_emp_barracks_1"]
    assert tf["name"] == "Training Field"
    assert (tf["chain"]["key"], tf["level"], tf["create_cost"]) == ("wh_main_EMPIRE_barracks", 0, 750)
    assert tf["cultures"] == ["wh_main_emp_empire"]


def test_empire_settlement_chain_availability(model):
    chain = model[1]["building_chain"]["wh_main_EMPIRE_settlement_major"]
    assert "wh_main_emp_empire" in {a["culture"]["key"] for a in chain["availability"] if a["culture"]}


def test_research_costs(model):
    by_type = model[1]
    tech = by_type["technology"]["wh2_dlc13_tech_emp_infantry_1_c"]
    assert tech["name"] == "Improved Heavy Weapons"
    assert {(p["tree"]["key"], p["research_points_required"]) for p in tech["placements"]} == {
        ("emp_civ_reworkd", 900), ("emp_wulfhart", 700)}
    costs = [p["resource_cost"] for t in by_type["technology"].values() for p in t["placements"]
             if p["resource_cost"] and p["resource_cost"]["key"] == "wh2_dlc09_tmb_tech_agent_unlock"]
    assert costs and costs[0]["treasury_cost"] == 0
    assert {"pooled_resource_factor": "canopic_jars_technology", "amount": -250, "context": "absolute"} in costs[0]["pooled_resources"]
    assert by_type["campaign_variable"]["base_research_points_per_turn"]["value"] == 100.0


def test_text_token_resolution(model):
    effect = model[1]["effect"]["wh_main_effect_technology_research_points"]
    assert effect["description"] == "Research rate: %+n"


def test_unit_set_membership(model):
    members = [u for u in model[1]["unit"].values()
               if any(s["key"] == "dlc14_all_units_excluding_characters" for s in u["unit_sets"])]
    assert len(members) == 1305


def test_factions_and_difficulty(model):
    by_type = model[1]
    reikland = by_type["faction"]["wh_main_emp_empire"]
    assert reikland["name"] == "Reikland" and reikland["culture"]["key"] == "wh_main_emp_empire"
    assert sorted(d["level"] for d in by_type["difficulty_level"].values()) == [-3, -2, -1, 0, 1, 2, 3]
    level2 = by_type["difficulty_level"]["2"]
    assert (len(level2["ai"]), len(level2["human"])) == (49, 0)


def test_altdorf_and_reikland(model):
    by_type = model[1]
    altdorf = by_type["region"]["wh3_main_combi_region_altdorf"]
    assert altdorf["name"] == "Altdorf"
    assert altdorf["province"]["key"] == "wh3_main_combi_province_reikland" and altdorf["is_province_capital"]
    assert altdorf["starting_owner"]["key"] == "wh_main_emp_empire" and altdorf["is_faction_capital"]
    assert altdorf["slot_cap"] == 10 and altdorf["template_source"] == "special"
    templates = {t["key"]: t for t in altdorf["slot_templates"]}
    assert {"wh_main_special_altdorf_primary", "wh_main_special_altdorf_secondary"} <= set(templates)
    primary = [c["key"] for c in templates["wh_main_special_altdorf_primary"]["permitted_chains"]]
    assert len(primary) == 54 and "wh2_dlc17_bst_special_settlement_altdorf" in primary
    assert len(templates["wh_main_special_altdorf_secondary"]["permitted_chains"]) == 469
    assert by_type["province"]["wh3_main_combi_province_reikland"]["capital"]["key"] == "wh3_main_combi_region_altdorf"


def test_grom_peak_resources(model):
    grom = model[1]["region"]["wh3_main_combi_region_grom_peak"]
    resources = {t["key"]: t["resource"] for t in grom["slot_templates"]}
    assert resources["wh2_dlc15_special_grom_peak_secondary"]["key"] == "res_rom_oil"
    assert resources["wh3_main_special_grom_peak_primary"]["key"] == "res_stone_trolls"
    assert resources["wh3_main_special_grom_peak_primary"]["name"] == "Stone Trolls Den"


def test_sea_region_is_not_a_settlement(model):
    sea = model[1]["region"]["wh3_main_chaos_region_kraken_sea"]
    assert sea["is_settlement"] is False and sea["province"] is None


def test_missing_links_do_not_exceed_baseline(model):
    ctx, _ = model
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    worse = {k: (v, baseline.get(k, 0)) for k, v in ctx.links.missing.items() if v > baseline.get(k, 0)}
    assert worse == {}, f"missing links above baseline (now, baseline): {worse}"


def test_unit_card_and_ability_icon_images(model):
    ctx, by_type = model
    require_images(ctx)
    assert by_type["unit"]["wh_main_emp_inf_greatswords"]["card_image"] == "ui/units/icons/wh_main_emp_greatswords.png"
    assert by_type["ability"]["wh2_dlc09_army_abilities_barrage_of_the_legion"]["icon_image"] == \
        "ui/battle ui/ability_icons/wh2_dlc09_army_abilities_barrage_of_the_legion.png"


def test_item_icon_faction_flag_and_unit_portrait_images(model):
    ctx, by_type = model
    require_images(ctx)
    assert by_type["item"]["wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead"]["icon_image"] == \
        "ui/campaign ui/ancillaries/wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead.png"
    assert by_type["faction"]["wh_main_emp_empire"]["flag_image"] == "ui/flags/wh_main_emp_empire/mon_64.png"
    assert by_type["unit"]["wh3_dlc26_ogr_cha_paymaster"]["portrait_image"] == \
        "ui/portraits/portholes/no_culture/ogr_paymaster_campaign_01_0.png"


def test_missing_images_do_not_exceed_baseline(model):
    ctx, _ = model
    require_images(ctx)
    baseline = json.loads(IMAGES_BASELINE.read_text(encoding="utf-8"))
    worse = {}
    for field, counts in ctx.images.stats.items():
        allowed = baseline.get(field, {})
        over = {k: (counts[k], allowed.get(k, 0)) for k in ("missing", "ambiguous") if counts[k] > allowed.get(k, 0)}
        if over:
            worse[field] = over
    assert worse == {}, f"image gaps above baseline (now, baseline): {worse}"
