using MoreDrugs.Content.Mdma;

namespace MoreDrugs.Tests;

public sealed class MdmaEconomyPolicyTests
{
    [Fact]
    public void MdmaIsPricedAboveNativeCocaine()
    {
        const float nativeCocaineBasePrice = 150f;

        Assert.True(
            MdmaEconomyPolicy.ProductPrice >
            nativeCocaineBasePrice);
    }

    [Fact]
    public void BatchEconomyMatchesLateGameTarget()
    {
        Assert.Equal(2_200f, MdmaEconomyPolicy.BatchRevenue);
        Assert.Equal(
            2_000f,
            MdmaEconomyPolicy.BatchGrossProfit(
                MdmaEconomyPolicy.SafroleLowPrice));
        Assert.Equal(
            1_925f,
            MdmaEconomyPolicy.BatchGrossProfit(
                MdmaEconomyPolicy.SafroleHighPrice));
    }

    [Fact]
    public void TabletPressIsALateGameCapitalPurchase()
    {
        Assert.Equal(5_000f, MdmaEconomyPolicy.TabletPressPrice);
    }
}
