# Guia de Modelos 3D

## Exportando do Blender para Web/AR

### Passo a passo
1. **Prepare o modelo**: Aplique todas as transforma&ccedil;&otilde;es (Ctrl+A)
2. **Texturas**: Use imagens .png ou .jpg, preferencialmente &lt;2048x2048
3. **Materiais**: Use Principled BSDF para compatibilidade
4. **Exportar**: File &gt; Export &gt; glTF 2.0 (.glb/.gltf)

### Configura&ccedil;&otilde;es de exporta&ccedil;&atilde;o glTF
- ✅ Apply Modifiers
- ✅ Include &gt; Selected Objects (opcional)
- ✅ Transform &gt; +Y Up
- ✅ Mesh &gt; UVs, Normais, Tangentes
- ✅ Mesh &gt; Vertex Colors (se usar)
- ✅ Anima&ccedil;&atilde;o (se tiver)
- ✅ Skinning (se tiver)
- ✅ Shape Keys (se tiver)
- ✅ Materiais: Exportar como glTF Embedded ou Binary (.glb)

### Formatos recomendados
- **.glb** (glTF Binary): &uacute;nico arquivo, ideal para web
- **.gltf + .bin + texturas**: m&uacute;ltiplos arquivos, bom para desenvolvimento
- **.usdz**: apenas para iOS AR Quick Look (converter com `xcrun realityconverter`)

## Modelos na pasta Materials/

### ✅ Prontos para AR
- `Mini_modern_house.glb`
- `Mech by Quaternius - o3Ps8z8ByP.glb`
- `realistic+interior.glb`
- `appartement.glb`
- `McLaren_P1_GTR_2015.usdz` (iOS)

### ⚠️ Requerem corre&ccedil;&atilde;o
- `scene.gltf` - Texturas com caminhos relativos quebrados
- `untitled kamer 309 .gltf` - Renomear (espa&ccedil;os no nome)
- `Art+Gallery+GLB.gltf` - URL encoded no nome

### 📦 Outros formatos
- `CurtainsSet-01.obj/.mtl/.fbx` - Converter para .glb
- `McLaren_P1_GTR_2015.usdz` - iOS apenas

## Ferramentas &uacute;teis

### Convers&atilde;o
- **Blender**: Exporta .glb nativamente
- **xcrun realityconverter** (macOS): .glb → .usdz
- **gltf-pipeline** (npm): Otimiza&ccedil;&atilde;o e convers&atilde;o
- **online 3D converter**: v&aacute;rios sites gratuitos

### Visualiza&ccedil;&atilde;o
- **model-viewer**: https://modelviewer.dev/
- **Three.js Editor**: https://threejs.org/editor/
- **Babylon.js Sandbox**: https://sandbox.babylonjs.com/

## Otimiza&ccedil;&atilde;o para Web

1. **Reduzir pol&iacute;gonos**: Decimate modifier no Blender
2. **Comprimir texturas**: .jpg para fotos, .png para gr&aacute;ficos
3. **Draco compression**: Reduz tamanho do .glb em at&eacute; 90%
4. **KTX2 textures**: Formato GPU-friendly (requer Three.js com extens&atilde;o)
5. **LOD (Level of Detail)**: M&uacute;ltiplas vers&otilde;es do modelo

## Licen&ccedil;as

- Verifique SEMPRE a licen&ccedil;a antes de usar
- **CC0**: Dom&iacute;nio p&uacute;blico, use livremente
- **CC-BY**: Atribua o autor
- **Editorial/Commercial**: Restri&ccedil;&otilde;es de uso
- **Sketchfab**: Cada modelo tem sua pr&oacute;pria licen&ccedil;a
