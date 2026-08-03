using MoreDrugs.Content.Mdma.Precursors;

namespace MoreDrugs.Tests;

public sealed class DiscoDaveyRelationshipDefaultsTests
{
    [Fact]
    public void StartsAtTheNativeNeutralRelationshipTier()
    {
        Assert.Equal(2f, DiscoDaveyRelationshipDefaults.InitialRelationshipDelta);
    }
}
