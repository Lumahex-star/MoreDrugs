using MoreDrugs.Content.Mdma.Precursors;
using MoreDrugs.Content.Mdma.Progression;

namespace MoreDrugs.Tests;

public sealed class MdmaProgressionPolicyTests
{
    [Fact]
    public void ProductDiscoveryRequiresFirstSuccessfulPress()
    {
        Assert.False(
            MdmaProgressionPolicy.ShouldDiscover(
                hasPressedFirstTablet: false));
        Assert.True(
            MdmaProgressionPolicy.ShouldDiscover(
                hasPressedFirstTablet: true));
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public void AmbiguousLegacyProductStateIsPreserved(
        bool discovered,
        bool listed)
    {
        Assert.True(
            MdmaProgressionPolicy.ShouldPreserveLegacyState(
                hasProgressionRecord: false,
                discovered,
                listed));
    }

    [Fact]
    public void RecordedAndFreshStatesNeedNoLegacyMigration()
    {
        Assert.False(
            MdmaProgressionPolicy.ShouldPreserveLegacyState(
                hasProgressionRecord: true,
                isDiscovered: true,
                isListed: true));
        Assert.False(
            MdmaProgressionPolicy.ShouldPreserveLegacyState(
                hasProgressionRecord: false,
                isDiscovered: false,
                isListed: false));
    }

    [Fact]
    public void SupplierCatalogContainsAllDistinctPrecursors()
    {
        Assert.Equal(3, MdmaPrecursorIds.SafroleOptions.Length);
        Assert.Equal(4, MdmaPrecursorIds.SupplierItems.Length);
        Assert.Equal(
            MdmaPrecursorIds.SupplierItems.Length,
            MdmaPrecursorIds.SupplierItems.Distinct().Count());
        Assert.All(
            MdmaPrecursorIds.SafroleOptions,
            id => Assert.Contains(
                id,
                MdmaPrecursorIds.SupplierItems));
        Assert.Contains(
            MdmaPrecursorIds.Methylamine,
            MdmaPrecursorIds.SupplierItems);
    }
}
