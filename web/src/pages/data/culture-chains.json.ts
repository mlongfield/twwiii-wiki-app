import type { APIRoute } from "astro";
import { getSite } from "../../data/model";
import { allCultureChains } from "../../lib/regionCultures";

export const GET: APIRoute = async () =>
  new Response(JSON.stringify(allCultureChains(await getSite())), {
    headers: { "Content-Type": "application/json" },
  });
