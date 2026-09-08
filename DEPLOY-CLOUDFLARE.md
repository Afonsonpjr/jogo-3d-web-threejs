# Deploy no Cloudflare Pages — Seila (3D, AR e VR)

Este guia mostra como colocar o projeto no ar usando **Cloudflare Pages**, de duas formas:

- Via **dashboard** (mais simples, só clicar).
- Via **Wrangler CLI** (mais controle, bom para scripts e CI/CD).

O projeto é estático (HTML/CSS/JS + modelos GLB/USDZ), então não precisa de build complexo.

---

## Estrutura de páginas

- `/` → `index.html` (redireciona para `/home.html`).
- `/home.html` → landing page com cards (Jogar, Sala AR, Multiplayer, Repositóºººrio).
- `/game.html` → jogo three.js com VR (WebXR).
- `/ar.html` → sala AR com `<model-viewer>`.

No Cloudflare Pages, todas essas URLs funcionarãºº diretamente, desde que os arquivos estejam na raiz do repositóºººrio.

---

## Opçººo A — Deploy via Dashboard (recomendado para começar)

### 1. Preparar o repositóºººrio no GitHub

Certifique-se de que no branch `main` estejam:

- `index.html`
- `home.html`
- `game.html`
- `ar.html`
- `Materials/` (com modelos GLB/USDZ)
- Demais assets (CSS, JS, etc., se houver).

### 2. Criar projeto no Cloudflare Pages

1. Acesse: https://dash.cloudflare.com/
2. Váºµ para **Workers & Pages** (menu lateral).
3. Clique em **Create application**.
4. Escolha a aba **Pages**.
5. Clique em **Connect to Git**.

### 3. Conectar o repositóºººrio

1. Selecione sua conta GitHub (se pedir autorizaçººo, aceite).
2. Escolha o repositóºººrio: `Afonsonpjr/jogo-3d-web-threejs`.
3. Clique em **Begin setup**.

### 4. Configurar o projeto

Preencha assim:

- **Project name**:  
  `jogo-3d-web-threejs` (ou outro nome que preferir).
- **Production branch**:  
  `main`.
- **Framework preset**:  
  `None` (ou "Static HTML", se aparecer).
- **Build command**:  
  Deixe **vazio**.
- **Build output directory**:  
  Deixe **vazio** (ou `/`, se pedir algo).
- **Root directory**:  
  Deixe como está (raiz do repo).

Isso diz ao Pages: "o site já está pronto, só sirva os arquivos da raiz".

### 5. Salvar e deployar

1. Clique em **Save and Deploy**.
2. O Cloudflare vai:
   - Clonar o repositóºººrio.
   - Fazer o deploy dos arquivos estáticos.
   - Gerar uma URL do tipo:  
     `https://jogo-3d-web-threejs.pages.dev`

### 6. Testar

Acesse:

- `https://jogo-3d-web-threejs.pages.dev/` → deve redirecionar para `/home.html`.
- `https://jogo-3d-web-threejs.pages.dev/home.html` → landing page.
- `https://jogo-3d-web-threejs.pages.dev/game.html` → jogo com VR.
- `https://jogo-3d-web-threejs.pages.dev/ar.html` → sala AR.

Teste em:

- Desktop (Chrome/Firefox/Edge).
- Android (Chrome) → AR via WebXR/Scene Viewer.
- iOS (Safari) → AR via Quick Look (modelos USDZ).

A cada `git push` no branch `main`, o Pages faz deploy automático.

---

## Opçººo B — Deploy via Wrangler CLI (avançººado)

Use esta opçººo se quiser:

- Deploy via terminal.
- Integrar com CI/CD (GitHub Actions, Azure DevOps, etc.).
- Mais controle sobre o processo.

### 1. Instalar Wrangler

No terminal, na pasta do projeto:

```bash
npm install -D wrangler
```

Ou global:

```bash
npm install -g wrangler
```

### 2. Fazer login

```bash
npx wrangler login
```

Isso abre o navegador para autorizar o Wrangler na sua conta Cloudflare.

### 3. Criar `wrangler.toml` (opcional para Pages simples)

Para Pages estático, você pode nem precisar de `wrangler.toml`, mas se quiser, crie algo como:

```toml
name = "jogo-3d-web-threejs"
compatibility_date = "2026-01-01"

[site]
bucket = "."
```

Isso diz que o "bucket" (pasta estática) é a raiz do projeto.

### 4. Deploy manual com Wrangler

Na raiz do projeto (onde estão `index.html`, `home.html`, etc.):

```bash
npx wrangler pages deploy .
```

Ou, se preferir apontar para uma pasta específica (ex: `public`), mova os arquivos para lá e use:

```bash
npx wrangler pages deploy public
```

O Wrangler vai:

- Fazer upload dos arquivos.
- Criar/atualizar o projeto Pages.
- Mostrar a URL de deploy (ex: `https://jogo-3d-web-threejs.pages.dev`).

### 5. Deploy contíººnuo (CI/CD) – visãºº geral

Para CI/CD, o fluxo típico é:

1. Criar um **API Token** da Cloudflare (no dashboard).
2. Guardar esse token como **secret** no seu provedor de CI (GitHub Actions, Azure, etc.).
3. No script de CI, rodar algo como:

```bash
npm install -D wrangler
npx wrangler pages deploy .
```

com as variáº½eis de ambiente:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID` (se necessáººrio).

A doc oficial de Wrangler tem exemplos prontos para GitHub Actions.

---

## Configuraçºµes recomendadas no Cloudflare

Depois que o site estiver no ar, vale ajustar:

### SSL/TLS

- Em **SSL/TLS**:
  - Modo: **Full** ou **Full (strict)** (se já tiver domíººdio).
  - Ativar **Always Use HTTPS**.

### Cache e performance

- Em **Speed > Optimization**:
  - Ativar **Auto Minify** para HTML, CSS e JS.
  - Ativar **Brotli** (se disponível).
- Em **Caching > Configuration**:
  - Níº½el de cache: **Standard**.
  - Opcional: criar **Page Rules** para:
    - `*.pages.dev/*` → Cache Everything por 1h (ou mais).

### HTTP/2 e HTTP/3

- Em **Network**:
  - Ativar **HTTP/3 (QUIC)**.
  - Manter **HTTP/2** ativado.

Isso melhora performance, especialmente em mobile.

---

## Domíººdio pró prio (futuro)

Quando quiser usar um domíººdio seu:

1. Comprar o domíººdio (ex: `seila.dev`).
2. No Cloudflare:
   - Adicionar site > inserir domíººdio.
   - Seguir o fluxo de mudar nameservers no registrador.
3. No projeto Pages:
   - Ir em **Custom domains**.
   - Adicionar `seila.dev` ou `app.seila.dev`.
4. Ajustar SSL/TLS para **Full (strict)**.

O deploy continua o mesmo; só muda a URL de acesso.

---

## Checklist rápido

- [ ] `index.html`, `home.html`, `game.html`, `ar.html` na raiz do repo.
- [ ] Branch `main` atualizado no GitHub.
- [ ] Projeto Pages criado e conectado ao GitHub.
- [ ] Framework preset: `None`, build command vazio.
- [ ] URL `https://<projeto>.pages.dev` acessíº½el.
- [ ] Testes feitos em:
  - Desktop.
  - Android (AR).
  - iOS (AR com USDZ).
  - Headset VR (se tiver).
- [ ] (Opcional) Wrangler instalado e deploy via CLI testado.
- [ ] (Futuro) Domíººdio pró prio configurado.
