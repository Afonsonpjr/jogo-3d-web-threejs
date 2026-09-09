# 🎮 Seila — 3D, AR e VR

Jogos 3D, Realidade Aumentada (AR) e Virtual (VR) rodando na Cloudflare Pages.

## 🚀 Demo

**URL:** https://jogo-3d-web-threejs.pages.dev/

## 📁 Páginas

| Página | Descrição | Tecnologia |
|--------|------------|------------|
| [Game 3D](public/game.html) | Cubo 3D girat�rio | Three.js |
| [AR](public/ar.html) | Astronauta em AR | model-viewer |
| [AR Viewer](public/ar-viewer.html) | Tê··nis 3D AR | model-viewer |
| [AR Mode](public/ar-mode.html) | Cadeira 3D AR | model-viewer |
| [Multiplayer](public/multiplayer.html) | Em desenvolvimento | - |

## 🛠 Tecnologias

- **Three.js** r0.160.0 - Renderiza����o 3D
- **Google model-viewer** v3.4.0 - AR/WebXR
- **Cloudflare Pages** - Deploy e hosting

## 📦 Estrutura

```
├── public/              # Site estático
│   ├── index.html       # Redirect
│   ├── home.html        # Menu principal
│   ├── game.html        # Three.js 3D
│   ├── ar.html          # AR Astronauta
│   ├── ar-viewer.html   # AR Tê··nis
│   ├── ar-mode.html     # AR Cadeira
│   └── multiplayer.html # Placeholder
├── admin/               # Dados administrativos
├── wrangler.jsonc       # Config Cloudflare
└── DEPLOY.md            # Instru����es de deploy
```

## 🚀 Deploy

Veja [DEPLOY.md](DEPLOY.md) para instru����es completas.

```bash
# Com wrangler CLI
wrangler deploy
```

## 📝 Pr�ximos Passos

- [ ] Adicionar modelos 3D pr�prios
- [ ] Implementar multiplayer (WebSocket/PeerJS)
- [ ] AR com modelos personalizados
- [ ] Analytics (Cloudflare Web Analytics)

---

**Status:** ✅ Produ����o  
**�ltima atualiza����o:** 2026-09-09
