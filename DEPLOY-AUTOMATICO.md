# 🚀 Deploy Autom�tico - Passo a Passo

## ⚡ Op��o 1: Cloudflare Dashboard (5 minutos)

### Passo 1: Acessar Cloudflare
1. Vá·· em: https://dash.cloudflare.com/
2. Faça login na sua conta

### Passo 2: Criar Pages
1. Menu lateral → **Workers & Pages**
2. Bot�o: **Create application**
3. Tab: **Pages**
4. Bot�o: **Connect to Git**

### Passo 3: Conectar Reposit�rio
1. Selecione sua conta GitHub: `Afonsonpjr`
2. Escolha o repo: `jogo-3d-web-threejs`
3. Bot�o: **Begin setup**

### Passo 4: Configurar Build
```
Project name: jogo-3d-web-threejs
Production branch: main
Build command: (deixe em branco)
Build output directory: public
```

### Passo 5: Deploy
1. Bot�o: **Save and Deploy**
2. Aguarde 1-2 minutos
3. URL gerada: `https://jogo-3d-web-threejs.pages.dev/`

### Passo 6: Testar
Acesse as URLs:
- https://jogo-3d-web-threejs.pages.dev/
- https://jogo-3d-web-threejs.pages.dev/game.html
- https://jogo-3d-web-threejs.pages.dev/ar.html

---

## ⚡ Op��o 2: Wrangler CLI (3 minutos)

### Pr�-requisitos
```bash
# Instalar Node.js (se n�o tiver)
# https://nodejs.org/

# Instalar wrangler
npm install -g wrangler
```

### Deploy
```bash
# Login
wrangler login

# Deploy
wrangler deploy

# Output:
# Deployed https://jogo-3d-web-threejs.pages.dev
```

---

## 📊 Status do Deploy

Ap�s deploy, verifique:

- [ ] Build passou (verde)
- [ ] URL funciona
- [ ] /game.html carrega
- [ ] /ar.html carrega
- [ ] Links funcionam

---

## 🐛 Troubleshooting

### Build falhou
- Verifique `public/` existe
- Confira `wrangler.jsonc` correto

### 404 nas p�ginas
- Build output directory: `public`
- Aguarde 2 minutos
- Hard refresh (Ctrl+Shift+R)

### AR n�o funciona
- Use HTTPS (Cloudflare j� fornece)
- Teste em mobile
- Permiss�es de c�mera

---

## 🔗 Links

- **Dashboard:** https://dash.cloudflare.com/
- **Seu Projeto:** https://dash.cloudflare.com/workers-and-pages
- **Docs:** https://developers.cloudflare.com/pages/

---

**Tempo total:** 5 minutos  
**Dificuldade:** F�cil ⭐
