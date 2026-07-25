using MoreDrugs.Content.Mdma.Batch;

namespace MoreDrugs.Tests;

public sealed class MdmaBatchProfileTests
{
    private const string BatchId = "0123456789abcdef0123456789abcdef";

    [Fact]
    public void CrystalBatchRejectsTabletPresentation()
    {
        Assert.Throws<ArgumentException>(() =>
            new MdmaBatchProfile(
                BatchId,
                MdmaProductForm.Crystals,
                80,
                75,
                5,
                tabletColor: MdmaTabletColor.Pink));
    }

    [Fact]
    public void PressPreservesChemistryAndAppliesBranding()
    {
        var crystals = new MdmaBatchProfile(
            BatchId,
            MdmaProductForm.Crystals,
            88,
            79,
            6,
            MdmaTestStatus.Verified);

        MdmaBatchProfile tablets = crystals.Press(
            MdmaTabletColor.Blue,
            MdmaTabletImprint.Star,
            "Night Shift");

        Assert.Equal(BatchId, tablets.BatchId);
        Assert.Equal(MdmaProductForm.Tablet, tablets.Form);
        Assert.Equal(88, tablets.Purity);
        Assert.Equal(79, tablets.Consistency);
        Assert.Equal(6, tablets.Contamination);
        Assert.Equal(MdmaTestStatus.Verified, tablets.TestStatus);
        Assert.Equal(MdmaTabletColor.Blue, tablets.TabletColor);
        Assert.Equal(MdmaTabletImprint.Star, tablets.TabletImprint);
        Assert.Equal("Night Shift", tablets.BrandName);
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(19, 0)]
    [InlineData(20, 1)]
    [InlineData(39, 1)]
    [InlineData(40, 2)]
    [InlineData(100, 2)]
    public void RiskUsesConsequentialContaminationBands(
        int contamination,
        int expected)
    {
        var profile = new MdmaBatchProfile(
            BatchId,
            MdmaProductForm.Crystals,
            70,
            70,
            contamination);

        Assert.Equal((MdmaBatchRisk)expected, profile.Risk);
    }

    [Fact]
    public void DifferentBatchIdsDoNotCompareEqual()
    {
        var first = new MdmaBatchProfile(
            BatchId,
            MdmaProductForm.Crystals,
            70,
            70,
            10);
        var second = new MdmaBatchProfile(
            "fedcba9876543210fedcba9876543210",
            MdmaProductForm.Crystals,
            70,
            70,
            10);

        Assert.NotEqual(first, second);
    }
}
