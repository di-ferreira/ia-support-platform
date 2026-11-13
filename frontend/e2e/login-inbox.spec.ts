import { expect, test, type Page } from "@playwright/test";

const email = process.env.E2E_EMAIL ?? "admin@emsoft.app";
const senha = process.env.E2E_SENHA ?? "admin123";

/**
 * Login, espera o inbox e abre o primeiro chat.
 * Skips legitimamente se a inbox estiver vazia.
 */
async function loginEAbrirPrimeiroChat(page: Page) {
  await page.goto("/login");
  await page.getByPlaceholder("seu@email.com").fill(email);
  await page.getByPlaceholder("••••••").fill(senha);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("**/dashboard");

  // Estabiliza o dashboard antes do full-reload: o guard de auth dispara
  // /auth/me ao carregar; navegar logo após o redirect o abortaria em voo,
  // e o catch do layout derruba a sessão. networkidle assenta em <1s.
  await page.waitForLoadState("networkidle");

  // Inbox: navega no client-side (link da sidebar) em vez de full-reload —
  // recarregar a página logo após o login pode abortar o /auth/me em voo e o
  // catch do layout derruba a sessão (redireciona para /login).
  await page.getByRole("link", { name: "Atendimento" }).click();
  await page.waitForURL("**/atendimento");
  const primeiroChat = page.getByTestId("inbox-chat-item").first();
  const inboxVazia = page.getByText("Nenhuma conversa");
  await expect(primeiroChat.or(inboxVazia).first()).toBeVisible({
    timeout: 15_000,
  });

  if (await page.getByTestId("inbox-chat-item").count() === 0) {
    test.skip(true, "inbox vazia — nenhum chat disponível para abrir");
  }

  // Abre o primeiro chat e espera as mensagens renderizarem
  await primeiroChat.click();
  const areaMensagens = page.getByTestId("chat-mensagens");
  await expect(areaMensagens).toBeVisible();
  await expect(
    areaMensagens
      .locator("> *")
      .first()
      .or(page.getByText("Nenhuma mensagem ainda"))
      .first(),
  ).toBeVisible({ timeout: 15_000 });
}

test.describe("Login → Inbox", () => {
  test("loga, abre a inbox e abre o primeiro chat", async ({ page }) => {
    await loginEAbrirPrimeiroChat(page);
  });

  test("envia mensagem real (opt-in)", async ({ page }) => {
    test.skip(
      !process.env.E2E_ENVIA_WHATSAPP,
      "envio real desativado (E2E_ENVIA_WHATSAPP não definido)",
    );

    await loginEAbrirPrimeiroChat(page);

    const campo = page.getByRole("textbox", { name: "Mensagem" });
    await campo.fill("Mensagem de teste E2E");
    await page.getByTestId("btn-enviar-mensagem").click();
    await expect(campo).toHaveValue("");
  });
});
