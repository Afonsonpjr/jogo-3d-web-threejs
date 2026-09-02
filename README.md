# 🎮 Jogo 3D Web - Three.js + Cannon.js

Jogo 3D web com f\u00edsica realista, sistema de agarrar e arremessar objetos.

## 🚀 Como Rodar

### Op\u00e7\u00e3o 1: Direto no Navegador

Simplesmente abra o arquivo `index.html` no seu navegador.

### Op\u00e7\u00e3o 2: Com Servidor Local (Recomendado)

```bash
# Usando Python
python -m http.server 8000

# Usando Node.js (npx)
npx serve .

# Usando PHP
php -S localhost:8000
```

Depois acesse: `http://localhost:8000`

## 🎯 Controles

| Tecla | A\u00e7\u00e3o |
|-------|-------|
| **W A S D** | Movimentar |
| **Shift** | Correr (2x velocidade) |
| **Mouse** | Olhar ao redor |
| **Clique** | Ativar controles / Agarrar-Soltar |
| **R** | Resetar objetos |

## 🛠 Tecnologias

- **Three.js** (r160): Renderiza\u00e7\u00e3o 3D
- **Cannon-es**: F\u00edsica de corpos r\u00edgidos
- **PointerLockControls**: Controles FPS

## 📦 Estrutura

```
jogo-3d-web-threejs/
\u251c\u2500\u2500 index.html          # Jogo completo (single-file)
\u2514\u2500\u2500 README.md           # Este arquivo
```

## 🎨 Funcionalidades

\u2705 Movimenta\u00e7\u00e3o FPS (WASD + Shift)  
\u2705 Sistema de agarrar objetos  
\u2705 Arremesso com f\u00edsica realista  
\u2705 20 objetos interativos (cubos, esferas, cilindros, cones)  
\u2705 Colis\u00f5es e gravidade  
\u2705 Indicador visual "PEGAR"  
\u2705 Sombras e ilumina\u00e7\u00e3o  

## 🔄 Pr\u00f3ximos Passos

### Adicionar Modelos 3D (.glb/.gltf)

1. Crie pasta `assets/models/`
2. Adicione seus modelos GLB
3. Use `GLTFLoader` do Three.js

Exemplo:
```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
loader.load('assets/models/meu-modelo.glb', (gltf) => {
    scene.add(gltf.scene);
});
```

### Otimizar com Draco

```bash
npm install -g @gltf-transform/cli
gltf-transform draco input.glb output.glb
```

### Expandir o Jogo

- Adicionar mais objetos
- Criar n\u00edveis/cen\u00e1rios
- Adicionar sons
- Sistema de pontua\u00e7\u00e3o
- Multiplayer (Socket.io)

## 📚 Recursos \u00dateis

- [Documenta\u00e7\u00e3o Three.js](https://threejs.org/docs/)
- [Cannon-es Examples](https://github.com/pmndrs/cannon-es)
- [Modelos Gratuitos (Sketchfab)](https://sketchfab.com)
- [Otimizar GLB](https://optimizeglb.com/)

## 📄 Licen\u00e7a

MIT - Use \u00e0 vontade!

---

Criado com ❤\ufe0f por Afonso Pereira
