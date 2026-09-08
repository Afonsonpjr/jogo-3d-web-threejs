# TODO — Seila (3D, AR e VR)

## ✅ Concluíºº

- [x] Criar `index.html` como redirect para `/home.html`.
- [x] Criar `home.html` como nova página inicial (cards: Jogar, Sala AR, Multiplayer, Repositóºººrio).
- [x] Criar `game.html` com:
  - WebXR habilitado (`renderer.xr.enabled = true`).
  - Botãºº VR via `VRButton.createButton(renderer)`.
  - Loop compatíº½el com VR (`renderer.setAnimationLoop`).
  - Controles PC (WASD, Shift, Espaço, V push-to-talk) e base para touch.
- [x] Criar `ar.html` como sala AR profissional com:
  - `<model-viewer>` v3.4.0.
  - `ar-modes="webxr scene-viewer quick-look fallback"`.
  - `camera-controls`, `auto-rotate`, `shadow-intensity`, `exposure`.
  - Lista de modelos (GLB + USDZ) com suporte a `ios-src` para Quick Look.
- [x] Organizar estrutura de páginas:
  - `/` → redirect para `/home.html`
  - `/home.html` → landing page
  - `/game.html` → jogo VR
  - `/ar.html` → sala AR
- [x] **Limpeza da pasta `Materials/`** — 7 arquivos removidos:
  - [x] `Art+Gallery+GLB.gltf` (24 MB)
  - [x] `scene.gltf` (221 KB)
  - [x] `untitled kamer 309 .gltf` (231 KB)
  - [x] `CurtainsSet-01.obj` (52 MB)
  - [x] `CurtainsSet-01.mtl` (706 bytes)
  - [x] `CurtainsSet-01.fbx` (16 MB)
  - [x] `CurtainsSet-01.mat` (61 KB)
  - **Total liberado:** ~93 MB

## ⚠️ Pendentes (prioridade)

### 1. Modelos 3D e AR

- [ ] Ajustar modelos principais no Blender:
  - [ ] Aplicar escala e roaçººo.
  - [ ] Colocar origem no chão (péºº do modelo em Y=0).
  - [ ] Exportar GLB com texturas embutidas (ou em pasta conhecida).
- [ ] Converter pelo menos 2–3 modelos chave para USDZ (para AR nativo em iOS):
  - [ ] `Mini_modern_house.usdz`
  - [ ] `realistic+interior.usdz`
  - [ ] `Mech.usdz` (opcional)
  - [ ] Atualizar `ar.html` com `ios-src` para esses modelos.

### 2. Jogo (game.html)

- [ ] Implementar física real (Cannon.js ou similar):
  - [ ] Colisãººo player–chãºº–objetos.
  - [ ] Pulo com gravidade.
  - [ ] Interaçººo (agarrar/empurrar objetos).
- [ ] Melhorar controles mobile:
  - [ ] Analóºººgico virtual (joystick) para movimento.
  - [ ] Botõºµºes: pulo, correr, interagir, agarrar.
  - [ ] Indicador visual de push-to-talk (V).
- [ ] Sistema de pontuaçººo/inventáººrio:
  - [ ] Pontos por coletáº½eis/interaçºµes.
  - [ ] HUD simples (pontos, itens).
- [ ] Carregamento de modelos:
  - [ ] Upload local de `.glb` (input file).
  - [ ] Spawn no chãºº com física.
- [ ] Multiplayer:
  - [ ] Integrar com `server/` (Socket.io).
  - [ ] Sincronizar posiçºµes dos players.
  - [ ] Chat de voz (push-to-talk) via WebRTC (opcional).

### 3. AR (ar.html)

- [ ] Melhorar UX da sala AR:
  - [ ] Thumbnails/preview dos modelos (imagens ou renders).
  - [ ] Descriçºµes curtas (uso, origem, licençºº).
  - [ ] Filtro por tipo (casa, objeto, veíº½ulo, etc.).
- [ ] Adicionar mais modelos de qualidade:
  - [ ] Buscar modelos GLB/USDZ de bancos gratuitos (Poly Haven, Sketchfab com licençºº adequada, etc.).
  - [ ] Testar em Android (WebXR/Scene Viewer) e iOS (Quick Look).
- [ ] Otimizar modelos para AR:
  - [ ] Reduzir políººgonos quando necessáººrio.
  - [ ] Ajustar materiais PBR para boa aparêº½ia em AR.
  - [ ] Garantir que o modelo fique estável no chãºº (sem flutuar).

### 4. Deploy e Infra (Cloudflare / GitHub Pages)

- [x] Criar `DEPLOY-CLOUDFLARE.md`.
- [ ] Testar deploy no Cloudflare Pages:
  - [ ] Validar URLs:
    - `https://<projeto>.pages.dev/` → redirect para `/home.html`
    - `/home.html`, `/game.html`, `/ar.html`.
  - [ ] Validar AR e VR em dispositivos reais (Android, iOS, headset VR).
- [ ] Opcional: configurar domíººdio pró prio no futuro:
  - [ ] Apontar DNS para Cloudflare.
  - [ ] Habilitar SSL, HTTP/2/3, cache e Page Rules.

### 5. Documentaçººo e UX

- [ ] Atualizar `README.md`:
  - [ ] Explicar estrutura de páginas (`/`, `/home.html`, `/game.html`, `/ar.html`).
  - [ ] Descrever recursos: VR, AR, multiplayer.
  - [ ] Links para `TODO.md` e `DEPLOY-CLOUDFLARE.md`.
- [ ] Adicionar instruçºµes de uso:
  - [ ] Como jogar (PC e mobile).
  - [ ] Como usar a sala AR (Android e iOS).
  - [ ] Requisitos (navegadores compatíº½eis com WebXR).
- [ ] Adicionar licençºº e créditos:
  - [ ] Licençºº dos modelos 3D.
  - [ ] Crêººditos para autores dos assets (ex: Quaternius).

## 🧭 Pró º º ºximos passos sugeridos

1. ✅ Limpeza concluíººa — pasta `Materials/` otimizada.
2. Ajustar 2–3 modelos no Blender e exportar GLB/USDZ otimizados.
3. Atualizar `ar.html` com esses modelos e `ios-src`.
4. Implementar física básica e controles mobile melhores em `game.html`.
5. Fazer deploy no Cloudflare Pages (seguir `DEPLOY-CLOUDFLARE.md`).
6. Testar tudo em:
   - Android (Chrome) → AR via WebXR/Scene Viewer.
   - iOS (Safari) → AR via Quick Look (USDZ).
   - Headset VR (ex: Meta Quest) → VR via WebXR.