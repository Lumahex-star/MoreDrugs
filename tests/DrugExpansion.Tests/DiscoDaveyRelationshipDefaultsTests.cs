using DrugExpansion.Content.Mdma.Precursors;

namespace DrugExpansion.Tests;

public sealed class DiscoDaveyRelationshipDefaultsTests
{
    [Fact]
    public void StartsAtTheNativeNeutralRelationshipTier()
    {
        Assert.Equal(2f, DiscoDaveyRelationshipDefaults.InitialRelationshipDelta);
    }
}
