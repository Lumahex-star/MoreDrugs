# Manual Tablet Press integration

The MoreDrugs tablet press follows the native Brick Press interaction contract,
but it must not reuse the native Brick Press product-conversion rule.

## Native behavior used as the reference

Schedule I's Brick Press exposes a narrow and useful mechanical contract:

- Clicking the handle begins a drag projected onto a handle-local plane.
- Cursor height between raised and lowered reference transforms maps to normalized
  progress from zero to one. Gamepad rotation input updates the same progress.
- The handle rotates through a complete 360-degree turn.
- The press head linearly interpolates between raised and lowered transforms.
- Releasing an unlocked handle lets it return toward zero.
- The task switches between pouring and pressing camera anchors, enables the
  handle only during the pressing phase, and completes at normalized progress one.

The native station then consumes 20 compatible product units and produces one
copy with brick packaging. That final rule is specific to bricks. The MDMA
station instead needs a server-authoritative crystals-to-tablets conversion that
preserves the custom batch identifier, purity, consistency, safety, color, and
imprint through save and multiplayer serialization.

## Exported runtime contract

`manual_tablet_press.glb` contains one reference animation named `PressCycle`.
Runtime station code must drive the mechanical assemblies directly; it must not
use the baked clip as authoritative gameplay.

| GLB node | Runtime role |
| --- | --- |
| `PedestalAssembly` | Floor-standing base; keeps the work surface at player height |
| `MachineAssembly` | Complete press mechanism mounted on the pedestal |
| `HandlePivot` | Rotate one full turn from normalized progress zero to one |
| `RamAssembly` | Move with press progress |
| `FeedShoeAssembly` | Slide on fixed guide rails from the hopper to the die |
| `FeedPowderAssembly` | Show powder in the shoe pocket before transfer |
| `DieFillAssembly` | Show transferred powder in the die until compression |
| `HandleClickableAnchor` | Center of the handle click target |
| `PlaneNormal` | Mouse-drag projection plane |
| `HandleRaised`, `HandleLowered` | Normalize pointer travel |
| `PressRaised`, `PressLowered` | Authoritative ram endpoints |
| `MouldDetector` | Die fill/detection volume center |
| `CameraPouring`, `CameraPressing` | Player task camera poses |
| `StandPoint` | Player alignment pose |
| `ContainerSpawnPoint` | Crystal input container pose |
| `OutputPoint` | Pressed-tablet output pose |

`ManualTabletPressAsset` loads the embedded GLB through MAPI, instantiates it,
and fails immediately if a required node was renamed or omitted.

The exported station is approximately 1.8 metres tall with a roughly one-metre
footprint and a 1.08-metre work surface. It is intended to be placed directly on
the floor, like the native Brick Press, rather than on furniture.

## Station implementation boundary

MoreDrugs registers a distinct buildable item definition by cloning the native
Brick Press definition. The cloned definition deliberately retains the native
`BuiltItem`, grid footprint, interaction task, item slots, FishNet object, save
data, and configuration lifecycle. A scoped runtime adapter recognizes only the
MoreDrugs item ID, hides that instance's native renderers, adds the authored GLB,
and redirects the native interaction anchors to the GLB contract above.

This consumer-side clone-and-adapt path does not mutate the native Brick Press
definition and does not require a new S1API prefab API. Existing Brick Press
instances and other mods retain their exact behavior.

The adapter replaces only the native final conversion for the MoreDrugs station:

1. Require 20 compatible MDMA crystal units from one batch.
2. Preserve the batch identifier, purity, consistency, contamination, and test
   status while adding the selected tablet color and imprint.
3. Create 20 tablet units, add them through the native replicated output slot,
   and consume the 20 crystal units through the native replicated input slots.
4. Reconstruct a deterministic settled tray from replicated output quantity on
   load or late join.
5. During a live press, guide each local tablet visual from the die toward the
   tray, then hand it to Unity physics with deterministic variation. These
   rigidbodies are cosmetic and never become authoritative network state.

The remaining validation boundary is in-game: host, joining client, reconnect,
save/reload, cancellation, full output, and mismatched-mod-version behavior in
both Mono and IL2CPP.

The native Brick Press is an interaction reference, not a logical product-type
template. This keeps the MDMA process distinct while retaining familiar Schedule I
controls and avoiding fragile global patches.

The feed shoe is mechanically constrained by two fixed guide rails. Its actuator
rod remains captured by a sleeve mounted to the frame throughout the stroke. At
rest, the hopper outlet and wiper seat against the shoe's powder pocket. During
the reference cycle, powder appears under the hopper, travels with the shoe,
transfers into the die as the shoe pocket empties, and disappears from the die
when the ram compresses it.
