import { defineConfig, type PlaywrightTestConfig } from "@playwright/test";

// webServer desligado por padrão: os testes rodam contra o container
// (aponte E2E_BASE_URL) ou contra `npm run dev` já em execução.
// Para subir o dev server automaticamente: E2E_WEBSERVER=1 npx playwright test
const config: PlaywrightTestConfig = {
  testDir: "./e2e",
  timeout: 30_000,
  retries: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    video: "off",
  },
  projects: [{ name: "chromium" }],
};

if (process.env.E2E_WEBSERVER === "1") {
  config.webServer = {
    command: "npm run dev",
    url: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    reuseExistingServer: true,
  };
}

export default defineConfig(config);
