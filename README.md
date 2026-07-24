# MoreDrugs

MoreDrugs is a real Schedule I mod and a public reference implementation for
S1API custom product kinds. Version 1 adds MDMA as the first content module.

The architecture is intentionally not MDMA-specific. Each module owns stable
product-kind and product IDs, persistence, presentation, packaging, production,
and optional mixing. A new custom drug kind does not need to be added to a central
enum and is not made non-mixable merely because Schedule I has no matching built-in
drug type.

## MDMA v1

- A custom logical MDMA product kind and fixed product definition.
- The mod-owned `Abstract Heart` GLB for loose, held, stored, station, functional,
  consumption, and generated inventory-icon presentation.
- Native baggie and jar shells populated with custom pill meshes; no extracted
  game packaging assets are redistributed.
- A Chemistry Station recipe using native station-capable ingredients.
- Save-provider reconstruction, Product Manager metadata, discovery, and listing.
- Mono and IL2CPP build targets.

Mixing is deliberately isolated from product identity. `MdmaModule` implements
the `IMixingCapability` boundary and explicitly selects a native mixer-map
execution strategy while preserving the custom MDMA kind for generated outputs.
The module is not reclassified as marijuana, methamphetamine, cocaine, or shrooms
simply to become mixable.

## Build

1. Copy `local.build.props.example` to `local.build.props`.
2. Update the local game, S1API, and MAPI assembly paths.
3. Build both runtimes:

```powershell
dotnet build .\src\MoreDrugs\MoreDrugs.csproj -c Mono
dotnet build .\src\MoreDrugs\MoreDrugs.csproj -c Il2cpp
```

Install the matching MoreDrugs DLL in the game `Mods` directory. Install the
matching S1API and S1MAPI builds as dependencies. All multiplayer peers need the
same mod and assets.

## Adding another drug

Implement `IDrugContentModule` in a new content folder and add it to the catalog
in `Core`. Keep the module's durable IDs stable after release. Mixing is an
independent optional capability; a native compatibility value is only a legacy
save/UI interoperability hint where the current game representation requires it.

## Testing policy

Pure unit tests may be committed. Runtime smoke mods, local game saves, extracted
game assets, generated wrappers, screenshots, and test launchers stay local and
must not be committed.

## Licenses

MoreDrugs source code is GPL-3.0-or-later. The bundled model is separately licensed
under CC BY 4.0; see [ASSET-LICENSE.md](ASSET-LICENSE.md).
