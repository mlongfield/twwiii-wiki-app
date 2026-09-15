import AbilityPage from "./AbilityPage.astro";
import BuildingChainPage from "./BuildingChainPage.astro";
import BuildingLevelPage from "./BuildingLevelPage.astro";
import CharacterPage from "./CharacterPage.astro";
import CulturePage from "./CulturePage.astro";
import FactionPage from "./FactionPage.astro";
import ItemPage from "./ItemPage.astro";
import ProvincePage from "./ProvincePage.astro";
import SkillPage from "./SkillPage.astro";
import SubculturePage from "./SubculturePage.astro";
import TechnologyPage from "./TechnologyPage.astro";
import TechnologyTreePage from "./TechnologyTreePage.astro";
import TraitPage from "./TraitPage.astro";
import UnitPage from "./UnitPage.astro";

/** Body component per page type; the entity route only builds pages for registered types. */
export const PAGE_BODIES = {
  unit: UnitPage,
  character: CharacterPage,
  skill: SkillPage,
  ability: AbilityPage,
  technology: TechnologyPage,
  technology_tree: TechnologyTreePage,
  building_level: BuildingLevelPage,
  building_chain: BuildingChainPage,
  item: ItemPage,
  trait: TraitPage,
  faction: FactionPage,
  culture: CulturePage,
  subculture: SubculturePage,
  province: ProvincePage,
};
