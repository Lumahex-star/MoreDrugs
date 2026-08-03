using DrugExpansion.Content.Mdma.Precursors;

namespace DrugExpansion.Tests;

public sealed class DiscoDaveyIdentityTests
{
    [Fact]
    public void RuntimeIdFollowsTheNativeNpcConvention()
    {
        Assert.Equal("disco_davey", MdmaPrecursorIds.DiscoDavey);
    }

    [Fact]
    public void SupplierPersistenceRetainsTheReleasedIdentity()
    {
        Assert.Equal(
            "ifbars.moredrugs:npcs/disco-davey",
            MdmaPrecursorIds.DiscoDaveyPersistentId);
        Assert.NotEqual(
            MdmaPrecursorIds.DiscoDavey,
            MdmaPrecursorIds.DiscoDaveyPersistentId);
    }
}
