import { buildInfo } from "../generated/build-info";
import { loadModel } from "./load";
import { createSite, type Site } from "./site";

let site: Promise<Site> | undefined;

/** The whole site's data, loaded once per build from the model the prebuild validated. */
export function getSite(): Promise<Site> {
  site ??= loadModel(buildInfo.modelDir).then(createSite);
  return site;
}

export { buildInfo };
