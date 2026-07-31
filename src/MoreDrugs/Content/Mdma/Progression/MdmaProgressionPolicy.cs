namespace MoreDrugs.Content.Mdma.Progression;

internal static class MdmaProgressionPolicy
{
    internal const int CurrentSchemaVersion = 1;

    internal static bool ShouldDiscover(bool hasPressedFirstTablet) =>
        hasPressedFirstTablet;

    internal static bool ShouldPreserveLegacyState(
        bool hasProgressionRecord,
        bool isDiscovered,
        bool isListed) =>
        !hasProgressionRecord && (isDiscovered || isListed);
}
