using MoreDrugs.Content.Mdma.Production;

namespace MoreDrugs.Content.Mdma;

internal static class MdmaEconomyPolicy
{
    internal const float ProductPrice = 220f;

    internal const float SafroleLowPrice = 70f;

    internal const float SafroleStandardPrice = 100f;

    internal const float SafroleHighPrice = 145f;

    internal const float MethylaminePrice = 90f;

    internal const float AcidPriceReference = 40f;

    internal const float TabletPressPrice = 5_000f;

    internal static float BatchRevenue =>
        ProductPrice *
        ManualTabletPressQuantities.ChemistryCrystalYield *
        ManualTabletPressQuantities.TabletsPerCycle;

    internal static float BatchInputCost(float safrolePrice) =>
        safrolePrice + MethylaminePrice + AcidPriceReference;

    internal static float BatchGrossProfit(float safrolePrice) =>
        BatchRevenue - BatchInputCost(safrolePrice);
}
