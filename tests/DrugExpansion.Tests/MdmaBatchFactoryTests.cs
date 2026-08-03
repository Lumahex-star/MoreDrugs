using DrugExpansion.Content.Mdma.Batch;

namespace DrugExpansion.Tests;

public sealed class MdmaBatchFactoryTests
{
    [Fact]
    public void BetterInputsAndControlImproveTheBatch()
    {
        Guid fixedId = Guid.Parse("01234567-89ab-cdef-0123-456789abcdef");

        MdmaBatchProfile poor = MdmaBatchFactory.CreateReaction(
            ingredientQuality: 0,
            processControl: 0.1,
            contaminationPressure: 0.9,
            () => fixedId);
        MdmaBatchProfile clean = MdmaBatchFactory.CreateReaction(
            ingredientQuality: 4,
            processControl: 0.9,
            contaminationPressure: 0.1,
            () => fixedId);

        Assert.True(clean.Purity > poor.Purity);
        Assert.True(clean.Consistency > poor.Consistency);
        Assert.True(clean.Contamination < poor.Contamination);
        Assert.True(clean.MarketScore > poor.MarketScore);
    }

    [Fact]
    public void FallbackIsStableAndExplicitlyUntested()
    {
        MdmaBatchProfile first =
            MdmaBatchFactory.CreateFallback(MdmaProductForm.Tablet);
        MdmaBatchProfile second =
            MdmaBatchFactory.CreateFallback(MdmaProductForm.Tablet);

        Assert.Equal(first, second);
        Assert.Equal(MdmaTestStatus.Untested, first.TestStatus);
        Assert.Equal(MdmaTabletColor.Pink, first.TabletColor);
        Assert.Equal(MdmaTabletImprint.Heart, first.TabletImprint);
    }
}
