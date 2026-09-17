from twwiki.model import build, campaigns, factions, schemas
from tests.model.fixtures import make_context, register_catalogs


def spf(faction, campaign, playable=False, is_major=False):
    return {"faction": faction, "campaign": campaign, "playable": playable, "is_major": is_major}


def faction_row(key):
    return {"key": key, "subculture": "", "category": "", "is_rebel": False, "is_quest_faction": False,
            "flags_path": "", "primary_colour_hex": ""}


def campaign_context():
    ctx = make_context({
        "campaigns": [
            {"campaign_name": "wh3_main_combi", "map_name": "wh3_main_combi_map_5",
             "script_path": "script/campaign/main_warhammer"},
            {"campaign_name": "wh3_main_chaos", "map_name": "wh3_main_chaos_map_4", "script_path": ""},
        ],
        "start_pos_factions": [
            spf("reikland", "wh3_main_combi", playable=True, is_major=True),
            spf("reikland", "wh3_main_chaos", is_major=True),
            spf("marienburg", "wh3_main_combi"),
            spf("reikland", "wh3_main_combi", playable=True, is_major=True),
        ],
        "factions": [faction_row("reikland"), faction_row("marienburg"), faction_row("nowhere")],
    }, loc={"campaigns_onscreen_name_wh3_main_combi": "Immortal Empires"})
    register_catalogs(ctx, campaigns, factions)
    return ctx


def test_campaigns_list_factions_by_start_position():
    ctx = campaign_context()
    built = {c["key"]: c for c in campaigns.build(ctx)["campaign"]}
    combi = built["wh3_main_combi"]
    assert combi["name"] == "Immortal Empires" and combi["map"] == "wh3_main_combi_map_5"
    assert combi["script_folder"] == "script/campaign/main_warhammer"
    assert [f["key"] for f in combi["factions"]] == ["marienburg", "reikland"]
    assert [f["key"] for f in combi["playable_factions"]] == ["reikland"]
    assert [f["key"] for f in combi["major_factions"]] == ["reikland"]
    chaos = built["wh3_main_chaos"]
    assert chaos["name"] is None and chaos["script_folder"] is None and chaos["playable_factions"] == []
    assert ctx.missing_names["campaign"] == 1
    for campaign in built.values():
        schemas.ENTITY_MODELS["campaign"].model_validate(campaign)


def test_factions_record_start_playable_and_major_campaigns():
    ctx = campaign_context()
    built = {f["key"]: f for f in factions.build(ctx)["faction"]}
    keys = lambda links: [link["key"] for link in links]
    reikland = built["reikland"]
    assert keys(reikland["start_campaigns"]) == ["wh3_main_chaos", "wh3_main_combi"]
    assert keys(reikland["playable_in"]) == ["wh3_main_combi"]
    assert keys(reikland["major_in"]) == ["wh3_main_chaos", "wh3_main_combi"]
    assert reikland["start_campaigns"][1]["name"] == "Immortal Empires"
    assert (built["nowhere"]["start_campaigns"], built["nowhere"]["playable_in"], built["nowhere"]["major_in"]) == ([], [], [])
    for faction in built.values():
        schemas.ENTITY_MODELS["faction"].model_validate(faction)


def test_campaign_module_is_built_and_regions_are_reverse_linked():
    assert campaigns in build.MODULES
    assert ("campaign", "regions", "campaign", "region") in build.REVERSE


def test_missing_campaigns_table_is_partial():
    ctx = make_context({"dummy": [{"a": 1}]})
    assert campaigns.build(ctx) == {"campaign": []}
    assert ctx.partial["campaign"] == ["campaigns"]
