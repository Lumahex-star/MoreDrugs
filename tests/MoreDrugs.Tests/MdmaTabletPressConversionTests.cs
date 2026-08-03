using MoreDrugs.Content.Mdma.Batch;

namespace MoreDrugs.Tests;

public sealed class MdmaTabletPressConversionTests
{
    private const string BatchId = "0123456789abcdef0123456789abcdef";

    [Theory]
    [InlineData(0)] // Trash
    [InlineData(1)] // Poor
    [InlineData(2)] // Standard
    [InlineData(3)] // Premium
    [InlineData(4)] // Heavenly
    public void PreservesEverySupportedCrystalQualityTier(int crystalQuality)
    {
        var crystals = new MdmaBatchProfile(
            BatchId,
            MdmaProductForm.Crystals,
            purity: 91,
            consistency: 84,
            contamination: 4,
            testStatus: MdmaTestStatus.Verified);

        MdmaPressedTabletBatch tablets =
            MdmaTabletPressConversion.Convert(crystals, crystalQuality);

        Assert.Equal(crystalQuality, tablets.Quality);
        Assert.Equal(MdmaProductForm.Tablet, tablets.Profile.Form);
        Assert.Equal(crystals.BatchId, tablets.Profile.BatchId);
        Assert.Equal(crystals.Purity, tablets.Profile.Purity);
        Assert.Equal(crystals.Consistency, tablets.Profile.Consistency);
        Assert.Equal(crystals.Contamination, tablets.Profile.Contamination);
        Assert.Equal(crystals.TestStatus, tablets.Profile.TestStatus);
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(5)]
    public void RejectsUnknownNativeQualityTiers(int crystalQuality)
    {
        var crystals = new MdmaBatchProfile(
            BatchId,
            MdmaProductForm.Crystals,
            purity: 55,
            consistency: 50,
            contamination: 20);

        Assert.Throws<ArgumentOutOfRangeException>(() =>
            MdmaTabletPressConversion.Convert(crystals, crystalQuality));
    }
}
