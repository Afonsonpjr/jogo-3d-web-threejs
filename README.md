# 🎮 Jogo 3D Web

Jogo 3D web com f&iacute;sica, AR, VR e multiplayer!

## 🚀 Como Rodar

### Op&ccedil;&atilde;o 1: Python (Recomendado)

```bash
# Instalar dependencias
pip install websocket-server

# Rodar servidor
python server.py

# Acessar
http://localhost:8000
```

### Op&ccedil;&atilde;o 2: Python Simples (apenas arquivos)

```bash
python -m http.server 8000

# Acessar
http://localhost:8000
```

### Op&ccedil;&atilde;o 3: Node.js (Multiplayer completo)

```bash
cd server
npm install
npm start

# Acessar
http://localhost:3000
```

## 📁 Estrutura

```
jogo-3d-web/
├── index.html          # Menu principal
├── game.html           # Jogo principal (HUD, fisica)
├── ar-mode.html        # Realidade Aumentada
├── vr-mode.html        # Realidade Virtual
├── multiplayer.html    # Multiplayer guest
├── server.py           # Servidor Python
└── server/
    ├── index.js        # Servidor Node.js
    └── package.json
```

## 🎮 Controles

- **WASD**: Mover
- **Shift**: Correr
- **Espa&ccedil;o**: Pular
- **Mouse**: Olhar
- **Clique**: Agarrar/Arremessar
- **1-5**: Invent&aacute;rio
- **H**: HUD

## ✨ Features

- ✨ F&iacute;sica realista (Cannon.js)
- ✨ AR/VR (WebXR)
- ✨ Multiplayer sem login
- ✨ HUD interativo
- ✨ Agarrar e arremessar objetos

## 🛠 Tecnologias

- Three.js (renderiza&ccedil;&atilde;o 3D)
- Cannon.js (f&iacute;sica)
- Socket.io / WebSocket (multiplayer)
- WebXR (AR/VR)

---

Criado por Afonso Pereira &copy; 2026
