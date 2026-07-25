# MDMA crystals asset contract

## Purpose

`mdma_crystals.glb` is a game-ready visual for the prepared crystalline batch
produced by MoreDrugs before it is converted into tablets. It must work as a
loose-item visual, generated icon source, station visual, and native-packaging
content source.

## Required form

- One compact pile with a readable ground contact.
- Eight to twelve irregular fractured chunks with varied proportions.
- A small number of scattered granules that visually connect to the pile.
- One `MdmaCrystals` root with four directly addressable mesh children:
  `CrystalPile`, `CrystalChunk_A`, `CrystalChunk_B`, and `CrystalGranules`.
- The four meshes must compose into one coherent full presentation while also
  remaining usable independently.
- Neutral, cloudy materials that can be tinted at runtime later.

The asset should read as processed crystalline material. It should not resemble
quartz points, gemstones, rock candy, fluorescent crystals, or a mound of fine
powder.

## Style and materials

- Stylized low-poly geometry with intentionally visible fracture planes.
- Cloudy warm-white, cool-white, and very restrained pale-rose variation.
- Opaque materials with moderate roughness; no glass transmission dependency.
- No textures, external files, or third-party source geometry.

## Technical limits

- Blender units are meters.
- Maximum extent: 0.12 m.
- Triangle budget: 3,000 evaluated triangles.
- Front axis: `-Y`; up axis: `+Z`.
- No animation or collision geometry.
- The GLB must import successfully in a clean Blender process.
- Required node and material names must survive GLB export.
- The exported runtime hierarchy must contain exactly the four named mesh
  variants beneath the root.

## Deliverables

- `tools/blender/create_mdma_crystals.py`
- `tools/blender/validate_mdma_crystals.py`
- `tools/blender/render_mdma_press_material_flow.py`
- `assets/source/mdma_crystals.blend`
- `src/MoreDrugs/Assets/Models/mdma_crystals.glb`
- Ignored multiview render evidence under `artifacts/`

## Tablet press presentation roles

- `CrystalPile`, `CrystalChunk_A`, and `CrystalChunk_B` communicate material
  loaded into the hopper.
- `CrystalGranules` is the only variant that travels with the mechanically
  connected feed shoe and appears in the die.
- The die granules disappear at compression as the actual heart-pill visual
  becomes available for ejection.
- Unity owns the authoritative state transitions and the guided-to-physics
  tablet ejection. The GLBs provide semantic visual parts, not gameplay state.

## Review questions

- Does the silhouette read as a small pile of fractured processed material?
- Do the chunks look irregular without becoming visually noisy?
- Do the materials remain readable at loose-item and inventory-icon scale?
- Does any fragment look unsupported, accidentally intersecting, or gem-like?
