import type { SkillTree } from "../generated/character";
import type { TechnologyTree } from "../generated/technology_tree";
import { skillDetailHtml, technologyDetailHtml } from "../lib/detailHtml";
import { type TreeLayout, layoutTree } from "../lib/treeLayout";
import { type Site, imageSrc, urlFor } from "./site";

export function skillTreeLayout(site: Site, tree: SkillTree): TreeLayout {
  const nodes = tree.nodes.map((n) => {
    const skill = site.model.entities.skill.get(n.skill.key);
    return {
      id: n.key,
      row: n.indent,
      column: n.tier,
      label: n.skill.name ?? n.skill.key,
      icon: imageSrc(site, skill?.icon_image),
      url: urlFor(site, "skill", n.skill.key),
      hidden: !n.visible_in_ui,
      detailHtml: skillDetailHtml(site, n.skill.key),
    };
  });
  return layoutTree(nodes, tree.links.map((l) => ({ parent: l.parent, child: l.child })));
}

export function technologyTreeLayout(site: Site, tree: TechnologyTree): TreeLayout {
  const nodes = tree.nodes.map((n) => {
    const tech = site.model.entities.technology.get(n.technology.key);
    return {
      id: n.key,
      row: n.indent,
      column: n.tier,
      label: n.technology.name ?? n.technology.key,
      icon: imageSrc(site, tech?.icon_image),
      url: urlFor(site, "technology", n.technology.key),
      hidden: false,
      detailHtml: technologyDetailHtml(site, n),
    };
  });
  return layoutTree(nodes, tree.links.map((l) => ({ parent: l.parent, child: l.child })));
}
