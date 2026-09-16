import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";

// The deploy workflow sets PUBLIC_SITE_URL (https://twwiii-wiki.web.app).
// Without it, local builds skip the sitemap with a warning.
export default defineConfig({
  output: "static",
  site: process.env.PUBLIC_SITE_URL,
  integrations: [react(), sitemap()],
  build: { format: "directory" },
});
