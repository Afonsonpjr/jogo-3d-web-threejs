# Compatibilidade de Modelos 3D

## ✅ Modelos Testados e Funcionais

| Modelo | Formato | AR iOS | AR Android | Web | Tamanho |
|--------|---------|--------|------------|-----|---------|
| Mini_modern_house | .glb | ✅ Quick Look | ✅ WebXR | ✅ | ~500KB |
| Mech (Quaternius) | .glb | ✅ Quick Look | ✅ WebXR | ✅ | ~1MB |
| realistic+interior | .glb | ✅ Quick Look | ✅ WebXR | ✅ | ~2MB |
| appartement | .glb | ✅ Quick Look | ✅ WebXR | ✅ | ~1.5MB |
| McLaren P1 GTR 2015 | .usdz | ✅ Quick Look | ❌ | ❌ | ~3MB |

## ⚠️ Modelos com Problemas

| Modelo | Problema | Solu&ccedil;&atilde;o |
|--------|----------|-------------|
| scene.gltf | Texturas com caminhos relativos quebrados | Reexportar como .glb embedded |
| untitled kamer 309 .gltf | Nome com espa&ccedil;os e acentos | Renomear para untitled_kamer_309.glb |
| Art+Gallery+GLB.gltf | URL encoded no nome | Renomear para Art_Gallery.glb |
| CurtainsSet-01.obj | Formato OBJ+MTL antigo | Converter para .glb no Blender |

## 📋 Requisitos para AR

### iOS (Quick Look)
- Formato: **.usdz** (obrigat&oacute;rio)
- ou **.glb** com atributo `ar` no model-viewer
- iOS 12+ no Safari

### Android (WebXR/Scene Viewer)
- Formato: **.glb** (recomendado)
- ou .gltf + .bin + texturas
- Chrome 74+ ou Samsung Internet

### Web (Visualizador 3D)
- Formato: **.glb** (ideal)
- .gltf (requer carregar texturas separadamente)
- .obj (limitado, sem materiais PBR)

## 🛠️ Como Corrigir

### scene.gltf (texturas quebradas)
1. Abrir no Blender
2. File &gt; Import &gt; glTF 2.0
3. Verificar se todas as texturas carregaram
4. File &gt; Export &gt; glTF 2.0
5. Marcar "Embed" para .glb &uacute;nico

### untitled kamer 309 .gltf
1. Renomear arquivo: `untitled_kamer_309.glb`
2. Atualizar refer&ecirc;ncias no c&oacute;digo
3. Testar no model-viewer

### CurtainsSet-01.obj
1. Abrir Blender
2. Importar OBJ
3. Aplicar materiais
4. Exportar como .glb

## 📊 Performance Recomendada

- **Pol&iacute;gonos**: &lt;50k para mobile, &lt;100k para desktop
- **Texturas**: &lt;2048x2048, preferir 1024x1024
- **Tamanho .glb**: &lt;5MB para web, &lt;2MB ideal
- **Draw calls**: Minimizar materiais distintos
- **Draco**: Ativar para reduzir tamanho em at&eacute; 90%
