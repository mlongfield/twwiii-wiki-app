from pathlib import Path

from twwiki.model import regions, schemas
from twwiki.model.images import ImageIndex
from tests.model.fixtures import make_context, register_catalogs

ALTDORF = "wh3_main_combi_region_altdorf"
GRUNBURG = "wh3_main_combi_region_grunburg"
SEA = "wh3_main_combi_region_kraken_sea"
BEACON = "wh3_prologue_region_ice_canyon_beacon_fort"
COPHER = "wh3_main_chaos_region_copher"
CHAINS = ["emp_settlement", "tmb_settlement", "chaos_altar", "altdorf_palace", "walls_1", "walls_2",
          "emp_barracks", "loop_chain"]


def spr(region, **o):
    row = {"region": region, "campaign": "wh3_main_combi", "owning_faction": "", "faction_capital": False,
           "slot_cap": 4, "cultural_originator": "wh_main_sc_emp_empire"}
    row.update(o)
    return row


def permitted(template, chain="", chain_set="", super_chain="", remove=False):
    return {"slot_template": template, "chain": chain, "chain_set": chain_set, "super_chain": super_chain,
            "remove": remove}


def set_item(set_key, chain, remove=False):
    return {"set": set_key, "chain": chain, "super_chain": "", "remove": remove}


def regions_context():
    ctx = make_context({
        "regions": [{"key": k} for k in [ALTDORF, GRUNBURG, SEA, BEACON, COPHER]],
        "start_pos_regions": [
            spr(ALTDORF, owning_faction="100", faction_capital=True, slot_cap=10),
            spr(GRUNBURG, owning_faction="999"),
            spr(BEACON, campaign="wh3_main_prologue", cultural_originator="wh_main_sc_ksl_kislev"),
            spr(COPHER, campaign="wh3_main_chaos", owning_faction="100"),
        ],
        "start_pos_factions": [{"ID": "100", "faction": "wh_main_emp_empire"}],
        "region_to_province_junctions": [
            {"province": "reikland", "region": ALTDORF, "is_capital": True},
            {"province": "reikland", "region": GRUNBURG, "is_capital": False},
            {"province": "ice_canyon", "region": BEACON, "is_capital": False},
        ],
        "provinces": [{"key": "reikland"}, {"key": "ice_canyon"}],
        "regions_to_region_groups_junctions": [
            {"region": ALTDORF, "region_group": "b_group", "order": 1},
            {"region": ALTDORF, "region_group": "a_group", "order": 0},
        ],
        "slot_templates": [
            {"key": "wh_main_special_altdorf_primary", "resource": ""},
            {"key": "wh_main_special_altdorf_secondary", "resource": "res_oil"},
            {"key": "wh3_cp1_special_altdorf_secondary_obsidian", "resource": ""},
            {"key": "wh2_dlc14_special_copher_port", "resource": ""},
            {"key": "wh3_dlc20_special_ice_canyon_beacon_fort_primary", "resource": "res_missing"},
            {"key": "wh2_main_special_nowhere_primary", "resource": ""},
            {"key": "generic_primary", "resource": ""},
        ],
        "slot_template_permitted_building_chains": [
            permitted("wh_main_special_altdorf_primary", chain_set="altdorf_set"),
            permitted("wh_main_special_altdorf_primary", super_chain="walls"),
            permitted("wh_main_special_altdorf_primary", chain="tmb_settlement", remove=True),
            permitted("wh_main_special_altdorf_secondary", chain="emp_barracks"),
        ],
        "building_chain_sets": [
            {"key": "generic_major", "parent_set": ""},
            {"key": "altdorf_set", "parent_set": "generic_major"},
            {"key": "loop_a", "parent_set": "loop_b"},
            {"key": "loop_b", "parent_set": "loop_a"},
        ],
        "building_chain_set_items": [
            set_item("generic_major", "emp_settlement"),
            set_item("generic_major", "tmb_settlement"),
            set_item("generic_major", "chaos_altar"),
            set_item("altdorf_set", "chaos_altar", remove=True),
            set_item("altdorf_set", "altdorf_palace"),
            set_item("loop_a", "loop_chain"),
        ],
        "building_chains": [{"key": k, "building_superchain": "walls" if k.startswith("walls") else ""}
                            for k in CHAINS],
        "resources": [{"key": "res_oil", "icon_filepath": "ui\\campaign ui\\effect_bundles\\resource_oil.png"}],
    }, loc={
        f"regions_onscreen_{ALTDORF}": "Altdorf",
        "provinces_onscreen_reikland": "Reikland",
        "resources_onscreen_text_res_oil": "Oil",
    })
    register_catalogs(ctx, regions)
    ctx.links.register("faction", {"wh_main_emp_empire": "Reikland"})
    ctx.links.register("subculture", {"wh_main_sc_emp_empire": "The Empire", "wh_main_sc_ksl_kislev": "Kislev"})
    ctx.links.register("building_chain", {k: None for k in CHAINS})
    ctx.links.register("campaign", {"wh3_main_combi": "Immortal Empires", "wh3_main_chaos": "The Realm of Chaos",
                                    "wh3_main_prologue": "The Lost God"})
    return ctx


def built(ctx):
    out = regions.build(ctx)
    return {r["key"]: r for r in out["region"]}, {p["key"]: p for p in out["province"]}


def test_region_stem():
    assert regions.region_stem(ALTDORF) == "altdorf"
    assert regions.region_stem(BEACON) == "ice_canyon_beacon_fort"
    assert regions.region_stem("no_marker_here") is None


def test_index_special_templates_reads_role_and_variant():
    index = regions.index_special_templates([
        "wh3_cp1_special_altdorf_secondary_obsidian",
        "wh2_dlc14_special_copher_port",
        "wh3_dlc20_special_ashrak_major_secondary_obsidian",
    ])
    assert index["altdorf"] == [{"key": "wh3_cp1_special_altdorf_secondary_obsidian", "role": "secondary",
                                 "variant": "obsidian"}]
    assert index["copher"] == [{"key": "wh2_dlc14_special_copher_port", "role": "port", "variant": None}]
    assert index["ashrak_major"][0]["variant"] == "obsidian"
    assert "ashrak" not in index


def test_chain_sets_apply_parents_removals_and_survive_cycles():
    chain_sets = regions.ChainSets(regions_context())
    assert chain_sets.chains_of_set("altdorf_set") == {"emp_settlement", "tmb_settlement", "altdorf_palace"}
    assert chain_sets.chains_of_set("loop_a") == {"loop_chain"}
    assert chain_sets.chains_of_set("unknown_set") == set()


def test_altdorf():
    ctx = regions_context()
    by_region, _ = built(ctx)
    altdorf = by_region[ALTDORF]
    assert altdorf["name"] == "Altdorf"
    assert altdorf["campaign"]["key"] == "wh3_main_combi" and altdorf["campaign"]["name"] == "Immortal Empires"
    assert altdorf["is_settlement"] is True
    assert (altdorf["province"]["key"], altdorf["province"]["name"]) == ("reikland", "Reikland")
    assert altdorf["is_province_capital"] is True and altdorf["is_faction_capital"] is True
    assert altdorf["starting_owner"]["key"] == "wh_main_emp_empire"
    assert altdorf["slot_cap"] == 10
    assert altdorf["cultural_originator"]["key"] == "wh_main_sc_emp_empire"
    assert altdorf["region_groups"] == ["a_group", "b_group"]
    assert altdorf["template_source"] == "special"
    assert [(t["key"], t["role"], t["variant"]) for t in altdorf["slot_templates"]] == [
        ("wh_main_special_altdorf_primary", "primary", None),
        ("wh3_cp1_special_altdorf_secondary_obsidian", "secondary", "obsidian"),
        ("wh_main_special_altdorf_secondary", "secondary", None),
    ]
    primary, _, secondary = altdorf["slot_templates"]
    assert [c["key"] for c in primary["permitted_chains"]] == ["altdorf_palace", "emp_settlement", "walls_1", "walls_2"]
    assert primary["resource"] is None
    assert secondary["resource"] == {"key": "res_oil", "name": "Oil", "icon_image": None}
    assert [c["key"] for c in secondary["permitted_chains"]] == ["emp_barracks"]
    schemas.ENTITY_MODELS["region"].model_validate(altdorf)


def test_generic_sea_prologue_port_and_counted_gaps():
    ctx = regions_context()
    by_region, _ = built(ctx)
    assert by_region[GRUNBURG]["starting_owner"] is None
    assert by_region[GRUNBURG]["template_source"] == "generic" and by_region[GRUNBURG]["slot_templates"] == []
    sea = by_region[SEA]
    assert (sea["is_settlement"], sea["campaign"], sea["province"], sea["slot_cap"], sea["cultural_originator"]) == \
        (False, None, None, None, None)
    assert by_region[BEACON]["slot_templates"][0]["resource"] == {"key": "res_missing", "name": None, "icon_image": None}
    assert by_region[COPHER]["slot_templates"][0]["role"] == "port"
    assert ctx.links.missing["region.starting_owner->faction"] == 1
    assert ctx.links.missing["region.province->province"] == 1
    assert ctx.links.missing["region.slot_template_resource->resources"] == 1
    assert ctx.manifest_sections["regions"] == {"special_templates_unmatched": 1}
    for region in by_region.values():
        schemas.ENTITY_MODELS["region"].model_validate(region)


def test_provinces():
    _, by_province = built(regions_context())
    reikland = by_province["reikland"]
    assert reikland["name"] == "Reikland" and reikland["campaign"]["key"] == "wh3_main_combi"
    assert [r["key"] for r in reikland["regions"]] == [ALTDORF, GRUNBURG]
    assert reikland["capital"]["key"] == ALTDORF
    ice = by_province["ice_canyon"]
    assert ice["capital"] is None and ice["campaign"]["key"] == "wh3_main_prologue"
    for province in by_province.values():
        schemas.ENTITY_MODELS["province"].model_validate(province)


def test_resource_icon_image_resolves_when_images_exist():
    ctx = regions_context()
    ctx.images = ImageIndex(Path("images"), ["ui/campaign ui/effect_bundles/resource_oil.png"])
    by_region, _ = built(ctx)
    assert by_region[ALTDORF]["slot_templates"][2]["resource"]["icon_image"] == \
        "ui/campaign ui/effect_bundles/resource_oil.png"


def test_manifest_section_defaults_when_regions_table_absent():
    ctx = make_context({"provinces": [{"key": "p"}]})
    regions.build(ctx)
    assert ctx.manifest_sections["regions"] == {"special_templates_unmatched": 0}
    assert ctx.partial["region"] == ["regions"]
