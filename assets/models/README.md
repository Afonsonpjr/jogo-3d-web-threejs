# Modelos 3D para AR

## ✅ Modelos compat&iacute;veis

### WebXR (Android) + Quick Look (iOS)
- `Mini_modern_house.glb`
- `Mech by Quaternius - o3Ps8z8ByP.glb`
- `realistic+interior.glb`
- `appartement.glb`

### Quick Look (iOS apenas)
- `McLaren_P1_GTR_2015.usdz`

## ⚠️ Modelos com problemas

- `scene.gltf` - Texturas com caminhos relativos quebrados
- `untitled kamer 309 .gltf` - Nome com espa&ccedil;os e acentos
- `Art+Gallery+GLB.gltf` - URL encoded

## 📦 Como adicionar seus pr&oacute;prios modelos

1. Exporte do Blender como **glTF Binary (.glb)**
2. Para iOS, converta para **USDZ** com `xcrun realityconverter`
3. Coloque em `Materials/` e atualize `ar-viewer.html`
