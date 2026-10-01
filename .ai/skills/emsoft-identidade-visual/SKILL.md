---
name: emsoft-identidade-visual
description: Identidade visual oficial da EMSoft Sistemas (emsoft.inf.br) para aplicar em qualquer projeto de software, site, dashboard, landing page, app ou interface desenvolvida por IA. Use este skill SEMPRE que o projeto for da EMSoft, mencionar EMSoft, emsoft.inf.br, ou quando o usuário pedir para aplicar "a identidade visual", "o padrão visual", "as cores da empresa" ou "o tema EMSoft". Define paleta de cores, tipografia, componentes (botões, cards, badges), gradientes e o botão obrigatório de tema claro/escuro.
---

# Identidade Visual EMSoft Sistemas

Fonte única da identidade: site oficial **https://www.emsoft.inf.br** (EMSoft Sistemas — ERP para Auto Peças). Todo projeto que usar este skill deve parecer parte da mesma família visual do site.

**Regras inegociáveis:**
1. Usar SEMPRE as variáveis CSS definidas abaixo — nunca cores hardcoded fora da paleta.
2. Todo projeto DEVE ter o botão de alternância de tema claro/escuro (código pronto na seção 6).
3. Tema claro é o padrão inicial.
4. Assinatura nos rodapés: `© EMSOFT. Todos os direitos reservados.`

---

## 1. Essência da marca

- **Personalidade:** tecnológica, confiável, profissional e acessível. Visual limpo, arejado, com cantos bem arredondados e sombras suaves.
- **Logo:** wordmark "EMsoft" — "EM" em azul-marinho, "soft" em laranja, com o tagline "s i s t e m a s" espaçado abaixo. Símbolo: chevron/"S" estilizado em azul com detalhe laranja.
- **Assinatura cromática:** azul royal dominante + laranja como cor de destaque. O laranja é usado com moderação — destaca UMA palavra em títulos, sublinha cards, colore ícones e números.

## 2. Paleta de cores (tokens CSS)

```css
:root {
  /* ===== MARCA ===== */
  --em-azul:          #1552C4;  /* azul primário — títulos, links, números */
  --em-azul-escuro:   #0A2A80;  /* navy — gradientes, fundos hero/footer */
  --em-azul-claro:    #1E5AD6;  /* azul vivo — fim de gradiente, hover */
  --em-laranja:       #F5821F;  /* laranja da marca — destaques, ícones */
  --em-ambar:         #F0C070;  /* âmbar — botão CTA principal */
  --em-verde:         #22A45D;  /* sucesso — badges "Seguro", checks */
  --em-teal:          #14B8A6;  /* acento secundário de cards */

  /* ===== TEMA CLARO (padrão) ===== */
  --bg:               #F4F7FB;  /* fundo de página / seções claras */
  --bg-card:          #FFFFFF;  /* fundo de cards */
  --bg-suave:         #EAF0F9;  /* seções alternadas, tiles de ícone */
  --texto:            #16325C;  /* texto principal (navy) */
  --texto-corpo:      #5C6B7F;  /* parágrafos, descrições */
  --texto-titulo:     var(--em-azul);
  --borda:            #E3EAF4;
  --sombra:           0 12px 30px rgba(10, 42, 128, 0.10);
  --grad-hero:        linear-gradient(135deg, #0A2A80 0%, #1E5AD6 100%);
  --texto-sobre-azul: #FFFFFF;
  --texto-sobre-azul-suave: #C9D6EE;
}

[data-theme="dark"] {
  /* ===== TEMA ESCURO (derivado do navy da marca) ===== */
  --bg:               #0B1B3A;
  --bg-card:          #13264D;
  --bg-suave:         #1A3059;
  --texto:            #E8EFFA;
  --texto-corpo:      #A9BBD8;
  --texto-titulo:     #7FA8FF;  /* azul clareado p/ contraste */
  --borda:            #24396A;
  --sombra:           0 12px 30px rgba(0, 0, 0, 0.45);
  --grad-hero:        linear-gradient(135deg, #061A52 0%, #123C9E 100%);
  --texto-sobre-azul: #FFFFFF;
  --texto-sobre-azul-suave: #C9D6EE;
  /* laranja, âmbar, verde e teal permanecem iguais nos dois temas */
}
```

**Proporção de uso:** ~60% fundos neutros (branco/navy), ~30% azul, ~10% laranja/âmbar. Verde e teal só como acentos pontuais.

## 3. Tipografia

- **Fonte:** `Poppins` (Google Fonts) — sans geométrica arredondada, idêntica ao estilo do site. Fallback: `Montserrat, 'Segoe UI', system-ui, sans-serif`.

```html
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```

```css
body { font-family: 'Poppins', Montserrat, 'Segoe UI', system-ui, sans-serif; }
```

- **Títulos (h1/h2):** peso 700–800, cor `--texto-titulo`. Em heros azuis: branco.
- **Destaque em títulos:** UMA palavra-chave em `--em-laranja` (padrão do site: "A evolução da <span class="destaque">sua</span> autopeça").
- **Corpo:** peso 400, cor `--texto-corpo`, line-height 1.7, tamanho 16–18px.
- **Números de estatísticas:** peso 800, tamanho gigante (3–4rem), alternando azul e laranja no mesmo número (ex.: "+ de" em uma cor, o valor na outra).
- **Tagline/labels pequenos:** letter-spacing alargado (0.3em), caixa baixa, remetendo ao "s i s t e m a s" do logo.

## 4. Componentes

### Botões (todos em formato pílula — `border-radius: 999px`)
```css
.btn { border-radius: 999px; padding: 14px 28px; font-weight: 700; border: none; cursor: pointer; font-family: inherit; transition: transform .15s ease, box-shadow .15s ease; }
.btn:hover { transform: translateY(-2px); box-shadow: var(--sombra); }

/* CTA principal — âmbar com texto navy (ex.: "Solicitar demonstração") */
.btn-primario { background: var(--em-ambar); color: #0A2A80; }

/* Secundário — branco com texto azul + ícone circular laranja (ex.: "Conheça mais um pouco »") */
.btn-secundario { background: var(--bg-card); color: var(--em-azul); }

/* Contorno — transparente com borda azul (ex.: "+ Depoimentos") */
.btn-contorno { background: transparent; color: var(--texto-titulo); border: 2px solid var(--em-azul); }

/* Link com seta (ex.: "fale conosco →") */
.btn-link { background: none; color: inherit; font-weight: 700; }
```
Ícones de chevron/seta (`›`, `»`, `→`) acompanham os botões de ação.

### Cards
- Fundo `--bg-card`, `border-radius: 24px`, sombra `--sombra`, padding generoso (28–32px).
- **Barra de acento inferior:** faixa arredondada de 6px em `--em-laranja` ou `--em-teal` na base do card (marca registrada do site).
- Cards escuros (destaque): fundo `--grad-hero`, texto branco, listas com check em círculo âmbar e divisórias finas translúcidas.

```css
.card { background: var(--bg-card); border-radius: 24px; box-shadow: var(--sombra); padding: 30px; }
.card-acento::after { content: ""; display: block; height: 6px; border-radius: 999px; background: var(--em-laranja); margin-top: 22px; width: 60%; }
```

### Badges / pills
- Formato pílula, texto pequeno e bold, ícone/emoji à esquerda.
- Sobre fundo azul: `background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25); color: #fff;`
- Status positivo: `background: #DCF5E4; color: var(--em-verde);` (no escuro: `background: rgba(34,164,93,.18)`).

### Tiles de ícone
Quadrado arredondado (radius 16px, ~56px) com fundo pastel da cor do ícone a 12–15% de opacidade: laranja, azul, verde ou teal.

### Listas de recursos
Item com ícone de check circular (âmbar sobre azul; verde sobre claro) + linha divisória fina `--borda` entre itens.

### Seções e heros
- Hero e footer: fundo `--grad-hero`, texto branco, marca d'água tipográfica gigante opcional (wordmark a ~5% de opacidade).
- Transições entre seções com curvas suaves (arcos arredondados no topo da seção seguinte).
- Seções claras alternam `--bg` e `--bg-suave`.

## 5. Layout e espaçamento

- Container máx. 1140px centralizado; padding lateral 24px.
- Espaço vertical generoso entre seções: 80–110px.
- Raio padrão: 24px (cards), 16px (tiles), 999px (botões/pills).
- Grid de cards: 2–3 colunas no desktop, 1 no mobile; leve sobreposição/offset entre cards no hero é bem-vinda.

## 6. Botão de tema claro/escuro (OBRIGATÓRIO)

Todo projeto deve incluir este botão, fixo no canto superior direito (ou dentro do header). Sol = ativa claro, lua = ativa escuro.

```html
<button id="botao-tema" class="botao-tema" aria-label="Alternar tema claro/escuro" title="Alternar tema">🌙</button>
```

```css
.botao-tema {
  position: fixed; top: 18px; right: 18px; z-index: 1000;
  width: 46px; height: 46px; border-radius: 999px; border: 1px solid var(--borda);
  background: var(--bg-card); color: var(--texto); font-size: 1.15rem;
  cursor: pointer; box-shadow: var(--sombra);
  display: grid; place-items: center; transition: transform .15s ease;
}
.botao-tema:hover { transform: scale(1.08); }
body, .card, .botao-tema { transition: background-color .3s ease, color .3s ease; }
```

```js
(function () {
  const btn = document.getElementById('botao-tema');
  const raiz = document.documentElement;
  let tema = 'light'; // padrão: claro
  try { tema = localStorage.getItem('emsoft-tema') || tema; } catch (e) { /* ambientes sem localStorage (ex.: artifacts) usam memória */ }
  aplicar(tema);
  btn.addEventListener('click', () => {
    tema = (tema === 'light') ? 'dark' : 'light';
    aplicar(tema);
    try { localStorage.setItem('emsoft-tema', tema); } catch (e) {}
  });
  function aplicar(t) {
    if (t === 'dark') { raiz.setAttribute('data-theme', 'dark'); btn.textContent = '☀️'; }
    else { raiz.removeAttribute('data-theme'); btn.textContent = '🌙'; }
  }
})();
```

Em projetos **React**, replicar a mesma lógica com `useState` + `useEffect` aplicando `data-theme` em `document.documentElement`, com o mesmo par de ícones 🌙/☀️.

## 7. Checklist de aplicação

Antes de entregar qualquer projeto com este skill, confira:

- [ ] Variáveis CSS da seção 2 copiadas integralmente (`:root` + `[data-theme="dark"]`)
- [ ] Fonte Poppins carregada com os pesos 400–800
- [ ] Botão de tema claro/escuro presente e funcional (tema claro como inicial)
- [ ] Botões em formato pílula; CTA principal em âmbar com texto navy
- [ ] Cards com radius 24px, sombra suave e barra de acento laranja/teal
- [ ] Títulos em azul (ou branco sobre azul) com uma palavra de destaque em laranja
- [ ] Hero/footer com gradiente navy → azul vivo
- [ ] Nenhuma cor fora da paleta; laranja usado com moderação (~10%)
- [ ] Rodapé com `© EMSOFT. Todos os direitos reservados.`
