# 🎮 Seila - 3D, AR e VR

Projeto de jogos 3D, Realidade Aumentada (AR) e Virtual (VR) rodando na Cloudflare Pages.

## 🚀 Como Testar

### 1. Jogo 3D (game.html)
- Acesse: `/game.html`
- **O que ver:** Cubo 3D colorido girando
- **Tecnologia:** Three.js
- **Intera��o:** Autom�tico (observa��o)

### 2. Realidade Aumentada (ar.html)
- Acesse: `/ar.html`
- **O que ver:** Astronauta 3D interativo
- **Tecnologia:** Google model-viewer
- **Intera��o:** Toque, zoom, rota����o, bot�o AR (mobile)

### 3. Multiplayer (multiplayer.html)
- Acesse: `/multiplayer.html`
- **Status:** Em desenvolvimento
- **Futuro:** WebSocket/PeerJS

## 📁 Estrutura

```
public/
├── index.html       → Redirect para home.html
├── home.html        → Menu principal
├── game.html        → Three.js 3D
├── ar.html          → AR com model-viewer
├── multiplayer.html → Placeholder
├── favicon.svg      → �cone
└── assets/          → Assets (modelos, texturas)
```

## 🛠 Tecnologias

| P�gina | Tecnologia | Vers�o |
|--------|------------|--------|
| game.html | Three.js | 0.160.0 |
| ar.html | model-viewer | 3.4.0 |

## 🌐 URLs

```
https://jogo-3d-web-threejs.pages.dev/
├── /game.html
├── /ar.html
└── /multiplayer.html
```

## 📝 Pr�ximos Passos

- [ ] Adicionar modelos 3D pr�prios
- [ ] Implementar multiplayer com WebSocket
- [ ] AR com modelos personalizados
- [ ] Anima��es e intera��es avan�adas

---

**Status:** ✅ B�sico funcionando
**Data:** 2026-09-09
