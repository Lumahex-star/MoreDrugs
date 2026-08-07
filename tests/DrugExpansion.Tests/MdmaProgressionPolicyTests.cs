using DrugExpansion.Content.Mdma.Precursors;
using DrugExpansion.Content.Mdma.Progression;

namespace DrugExpansion.Tests;

public sealed class MdmaProgressionPolicyTests
{
    [Fact]
    public void NewSaveInitializesProgressionState()
    {
        MdmaProgressionData result = MdmaProgressionPolicy.Initialize(
            data: null,
            hadProgressionRecord: false,
            isDiscovered: false,
            isListed: false);

        Assert.Equal(MdmaProgressionPolicy.CurrentSchemaVersion, result.SchemaVersion);
        Assert.False(result.HasPressedFirstTablet);
        Assert.False(result.LegacyDiscoveryStatePreserved);
    }

    [Fact]
    public void ExistingProgressionStateIsPreserved()
    {
        var existing = new MdmaProgressionData
        {
            SchemaVersion = 0,
            HasPressedFirstTablet = true,
        };

        MdmaProgressionData result = MdmaProgressionPolicy.Initialize(
            existing,
            hadProgressionRecord: true,
            isDiscovered: true,
            isListed: false);

        Assert.Same(existing, result);
        Assert.Equal(MdmaProgressionPolicy.CurrentSchemaVersion, result.SchemaVersion);
        Assert.True(result.HasPressedFirstTablet);
        Assert.False(result.LegacyDiscoveryStatePreserved);
    }

    [Fact]
    public void MissingLegacyRecordPreservesKnownProductState()
    {
        MdmaProgressionData result = MdmaProgressionPolicy.Initialize(
            data: null,
            hadProgressionRecord: false,
            isDiscovered: true,
            isListed: false);

        Assert.True(result.LegacyDiscoveryStatePreserved);
    }

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
