# Disco Davey and MDMA Precursor Integration Plan

## Goals

- Keep MDMA undiscovered and unlisted until gameplay progression earns it.
- Add a native-style custom supplier, Disco Davey.
- Add supplier-sourced precursor items without exposing them as sellable products.
- Replace the placeholder pseudo-based MDMA crystal recipe with a fictionalized,
  game-oriented precursor flow.
- Ship original, reproducible assets that visually fit Schedule I without
  redistributing game-owned meshes or prefabs.

## Availability and Progression Rules

Registration is not progression. Building the MDMA definition and registering
its Product Manager metadata must not discover or list it.

Recommended progression:

1. Disco Davey begins locked and unknown as a supplier.
2. A later introduction objective unlocks Davey and his precursor listings.
3. Davey sells Safrole in three quality tiers and one fixed-quality Methylamine
   item.
4. The Chemistry Station recipe becomes available with the supplier introduction,
   but MDMA itself remains undiscovered.
5. Completing the first successful tablet-press cycle discovers MDMA with
   `listForSale: false`.
6. Listing MDMA for customers remains an explicit player action through the
   native Product Manager flow.

This separation allows players to know the supplier and recipe without treating
MDMA as a market-ready product before they have made it.

### Previously affected saves

The old build persisted MDMA in the native discovered/listed product collections.
The initial bug fix stops adding it on load but does not blindly remove saved
state. Once MoreDrugs owns a versioned progression record, a one-time migration
can remove legacy discovery/listing only when that record proves the player has
never legitimately completed an MDMA batch.

## Content Identities

Treat these IDs as persistent save contracts:

| Content | Stable ID |
| --- | --- |
| Disco Davey | `ifbars.moredrugs:npcs/disco-davey` |
| Low-quality Safrole | `ifbars.moredrugs:ingredients/safrole-low` |
| Safrole | `ifbars.moredrugs:ingredients/safrole` |
| High-quality Safrole | `ifbars.moredrugs:ingredients/safrole-high` |
| Methylamine | `ifbars.moredrugs:ingredients/methylamine` |

Console aliases can expose `safrole`, `safrolelow`, `safrolehigh`, and
`methylamine` without weakening the persistent namespaced IDs.

## Precursor Items

### Safrole

Implement three registered `QualityItemDefinition` records, following the native
pseudo supplier pattern:

| Variant | Default quality | Initial price target | Role |
| --- | --- | --- | --- |
| Low-quality Safrole | Poor | $70 | Cheap input with higher batch risk |
| Safrole | Standard | $100 | Normal production input |
| High-quality Safrole | Premium | $145 | Expensive input with improved batch quality |

All three definitions share the same stored, held, station, and icon asset family.
Quality remains visible through the native quality UI and can additionally change
the bottle label or liquid clarity.

Safrole is an ingredient, not a product: it is not consumable, packageable,
discoverable in Product Manager, or sellable to customers.

### Methylamine

Implement one fixed-quality storable ingredient initially. Its purpose is to
create a supply bottleneck and a second supplier-order decision, not another
quality axis. It is not consumable, packageable, or customer-sellable.

If later batch design needs Methylamine purity to matter independently, add
quality variants additively rather than changing the original item identity.

## Disco Davey

Implement `DiscoDavey : S1API.Entities.NPC` as a physical supplier:

- `IsPhysical => true`
- `IsSupplier => true`
- stable identity configured through `NPCPrefabBuilder.WithIdentity(...)`
- locked relationship defaults using `SetUnlocked(false)`
- native supplier infrastructure through `WithSupplierDefaults(...)`
- delivery listings for all three Safrole variants and Methylamine
- host-authoritative unlock through `NPCSupplier.Unlock()`

Character direction:

- friendly, sketchy, and immediately sociable;
- colorful party clothes, slightly disheveled appearance, sunglasses or another
  nightlife accessory;
- the `hippie` or `tyler` voice family at a modest pitch adjustment;
- a late-day/night schedule around a nightlife-adjacent public location;
- supplier text that hints at parties and an off-book chemical connection
  without giving real synthesis instructions.

Suggested supplier copy:

- Recommendation: `My friend Disco Davey always knows where the afterparty is. He can also get some unusual lab supplies. I've passed your number on to him.`
- Unlock hint: `You can now order Safrole and Methylamine from Disco Davey. They are precursor supplies for your MDMA operation.`

Spawn position, precise schedule locations, appearance paths, and the recommending
NPC remain explicit review decisions after an in-game location pass.

## Production Integration

Replace the placeholder pseudo ingredient options after the precursor items exist.
Keep the recipe fictionalized and mechanically legible:

- one Safrole quality variant controls the native recipe quality input;
- Methylamine is a required fixed-quality reagent;
- a third generic in-game laboratory reagent may remain if pacing needs another
  purchase source;
- Chemistry Station output remains MDMA Crystals;
- the Manual Tablet Press remains the only crystal-to-tablet process.

Do not discover MDMA when Davey unlocks, when ingredients are purchased, or when
crystals are created. Discover it after the first successful tablet press output,
without automatically listing it.

## Asset Contracts

Blender 5.2.0 LTS is the current deterministic generation runtime. Each asset
will use a source-controlled Python generator plus generated `.blend` and `.glb`
outputs. Game-owned Acid, Phosphorus, and pseudo assets are local visual evidence
only and will not be redistributed.

### Safrole bottle

```json
{
  "asset": "Safrole bottle family",
  "purpose": "stored, held, station, supplier, and icon presentation",
  "required_parts": [
    "amber reagent bottle",
    "dark screw cap",
    "cream product label",
    "visible golden-brown liquid",
    "low, standard, and high quality label variants"
  ],
  "style": ["Schedule I stylized", "clean low-poly", "readable at inventory scale"],
  "limits": {
    "triangle_max": 2500,
    "maximum_extent_m": 0.24,
    "material_max": 6
  },
  "review_questions": [
    "Does it read as a specialty liquid precursor rather than Acid?",
    "Are quality variants distinguishable without becoming noisy?",
    "Does the cap and bottle support believable Chemistry Station pouring?"
  ]
}
```

Recommended GLB hierarchy:

- `SafroleBottle`
- `SafroleLiquid`
- `SafroleLabel_Low`
- `SafroleLabel_Standard`
- `SafroleLabel_High`

### Methylamine container

```json
{
  "asset": "Methylamine chemical jug",
  "purpose": "stored, held, station, supplier, and icon presentation",
  "required_parts": [
    "compact opaque chemical jug",
    "molded handle",
    "sealed screw cap",
    "fictional warning label",
    "stable flat base"
  ],
  "style": ["Schedule I stylized", "industrial laboratory supply", "clean low-poly"],
  "limits": {
    "triangle_max": 2800,
    "maximum_extent_m": 0.28,
    "material_max": 5
  },
  "review_questions": [
    "Is it visually distinct from Safrole and the native Acid bottle?",
    "Does the handle remain readable in the held and icon views?",
    "Can its station version pour without an implausible pivot?"
  ]
}
```

Recommended GLB hierarchy:

- `MethylamineJug`
- `MethylamineCap`
- `MethylamineLabel`
- `MethylamineLiquidWindow` (optional)

## Delivery Phases

1. **Availability fix**
   - Remove automatic MDMA discovery/listing.
   - Validate Mono and IL2CPP.

2. **Item definitions**
   - Add stable IDs and console aliases.
   - Register Safrole variants and Methylamine before supplier prefab setup.
   - Use temporary generated icons only if final GLBs are not ready.

3. **Asset production**
   - Generate Safrole and Methylamine assets from deterministic Blender scripts.
   - Fresh-import validate GLBs.
   - Inspect hero, orthographic, held, stored, station, and icon renders.

4. **Supplier integration**
   - Add Disco Davey’s supplier prefab, relationship defaults, appearance,
     schedule, listings, and messaging.
   - Verify dead drops, meetings, delivery unlocks, save/reload, and late join.

5. **Progression and recipe**
   - Add versioned progression state.
   - Unlock Davey through a selected introduction trigger.
   - Replace pseudo in the crystal recipe.
   - Discover but do not list MDMA after the first successful press.
   - Migrate only provably legacy-contaminated saves.

6. **Validation**
   - Unit-test IDs, item qualities, registration order, and progression policy.
   - Build Mono and IL2CPP.
   - Manually test fresh save, existing clean save, affected legacy save,
     supplier unlock, order delivery, recipe production, first press discovery,
     explicit listing, save/reload, and multiplayer host/client replication.
