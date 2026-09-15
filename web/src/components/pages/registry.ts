import AbilityPage from "./AbilityPage.astro";
import ItemPage from "./ItemPage.astro";
import SkillPage from "./SkillPage.astro";
import TraitPage from "./TraitPage.astro";
import UnitPage from "./UnitPage.astro";

/** Body component per page type; the entity route only builds pages for registered types. */
export const PAGE_BODIES = {
  unit: UnitPage,
  ability: AbilityPage,
  skill: SkillPage,
  item: ItemPage,
  trait: TraitPage,
};
