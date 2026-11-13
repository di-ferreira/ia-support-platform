import { expect, test } from "@playwright/test";

const email = process.env.E2E_EMAIL ?? "admin@emsoft.app";
const senha = process.env.E2E_SENHA ?? "admin123";

test.describe("Login → Inbox", () => {
  test("loga, abre a inbox e interage com o chat", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("seu@email.com").fill(email);
    await page.getByPlaceholder("••••••").fill(senha);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.waitForURL("**/dashboard");

    // Inbox: espera a lista terminar de carregar (vazia ou com chats)
    await page.goto("/atendimento");
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

    // Digita no campo de envio (sempre) — o clique em enviar é real só se autorizado
    const campo = page.getByRole("textbox", { name: "Mensagem" });
    await campo.fill("Mensagem de teste E2E");

    test.skip(
      !process.env.E2E_ENVIA_WHATSAPP,
      "envio real desativado (E2E_ENVIA_WHATSAPP não definido)",
    );
    await page.getByTestId("btn-enviar-mensagem").click();
    await expect(campo).toHaveValue("");
  });
});
