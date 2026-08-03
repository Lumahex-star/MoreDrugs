using DrugExpansion.Content.Mdma;

namespace DrugExpansion.Tests;

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
        Assert.Equal(1_900f, MdmaEconomyPolicy.BatchRevenue);
        Assert.Equal(
            1_680f,
            MdmaEconomyPolicy.BatchGrossProfit(
                MdmaEconomyPolicy.SafroleLowPrice));
        Assert.Equal(
            1_595f,
            MdmaEconomyPolicy.BatchGrossProfit(
                MdmaEconomyPolicy.SafroleHighPrice));
    }

    [Fact]
    public void SupplierLimitsMatchNativeLateGameSuppliers()
    {
        Assert.Equal(400f, MdmaEconomyPolicy.SupplierStartingOrderLimit);
        Assert.Equal(2_000f, MdmaEconomyPolicy.SupplierMaximumOrderLimit);
        Assert.True(
            MdmaEconomyPolicy.SupplierStartingOrderLimit >=
            MdmaEconomyPolicy.SafroleStandardPrice +
            MdmaEconomyPolicy.MethylaminePrice);
    }

    [Fact]
    public void TabletPressIsALateGameCapitalPurchase()
    {
        Assert.Equal(5_000f, MdmaEconomyPolicy.TabletPressPrice);
    }
}
