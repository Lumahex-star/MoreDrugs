#if IL2CPPMELON
using Il2CppInterop.Runtime.InteropTypes;
using S1ItemFramework = Il2CppScheduleOne.ItemFramework;
using S1ObjectScripts = Il2CppScheduleOne.ObjectScripts;
#elif MONOMELON
using S1ItemFramework = ScheduleOne.ItemFramework;
using S1ObjectScripts = ScheduleOne.ObjectScripts;
#endif

using HarmonyLib;

namespace MoreDrugs.Content.Mdma.Production;

/// <summary>
/// Prevents the native Lab Oven from treating the tablet-press intermediate as
/// a cookable cocaine-base derivative.
/// </summary>
internal static class MdmaCrystalLabOvenPatches
{
    private static bool IsCrystal(S1ItemFramework.ItemInstance? item) =>
        item != null &&
        string.Equals(
            item.ID,
            MdmaProductIds.Crystals,
            StringComparison.OrdinalIgnoreCase);

    private static bool IsIngredientSlot(
        S1ItemFramework.ItemSlot slot,
        out S1ObjectScripts.LabOven? oven)
    {
        oven = AsLabOven(slot.SlotOwner);
        return oven != null &&
               (ReferenceEquals(oven.IngredientSlot, slot) ||
                oven.IngredientSlot == slot);
    }

#if IL2CPPMELON
    private static S1ObjectScripts.LabOven? AsLabOven(
        S1ItemFramework.IItemSlotOwner? owner) =>
        owner?.TryCast<S1ObjectScripts.LabOven>();
#else
    private static S1ObjectScripts.LabOven? AsLabOven(
        S1ItemFramework.IItemSlotOwner? owner) =>
        owner as S1ObjectScripts.LabOven;
#endif

    [HarmonyPatch(
        typeof(S1ItemFramework.ItemSlot),
        nameof(S1ItemFramework.ItemSlot.DoesItemMatchHardFilters))]
    private static class IngredientSlotFilterPatch
    {
        private static bool Prefix(
            S1ItemFramework.ItemSlot __instance,
            S1ItemFramework.ItemInstance item,
            ref bool __result)
        {
            if (!IsCrystal(item) ||
                !IsIngredientSlot(__instance, out _))
            {
                return true;
            }

            __result = false;
            return false;
        }
    }

    [HarmonyPatch(
        typeof(S1ObjectScripts.LabOven),
        nameof(S1ObjectScripts.LabOven.IsIngredientCookable))]
    private static class CookabilityPatch
    {
        private static bool Prefix(
            S1ObjectScripts.LabOven __instance,
            ref bool __result)
        {
            if (!IsCrystal(__instance.IngredientSlot?.ItemInstance))
                return true;

            __result = false;
            return false;
        }
    }
}
