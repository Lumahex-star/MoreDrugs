using MoreDrugs.Content.Mdma.Production;

namespace MoreDrugs.Tests;

public sealed class ManualTabletPressQuantitiesTests
{
    [Fact]
    public void ChemistryBatchRequiresOnePressPerCrystal()
    {
        Assert.Equal(20, ManualTabletPressQuantities.ChemistryCrystalYield);
        Assert.Equal(1, ManualTabletPressQuantities.CrystalsPerCycle);
        Assert.Equal(1, ManualTabletPressQuantities.TabletsPerCycle);
        Assert.Equal(
            ManualTabletPressQuantities.ChemistryCrystalYield,
            ManualTabletPressQuantities.ChemistryCrystalYield /
            ManualTabletPressQuantities.CrystalsPerCycle);
    }

    [Fact]
    public void OneArmedCycleCanCommitExactlyOnce()
    {
        var gate = new ManualTabletPressCompletionGate();

        gate.Arm();

        Assert.True(gate.TryCommit());
        Assert.False(gate.TryCommit());
    }

    [Fact]
    public void StartingAnotherCycleRearmsCompletion()
    {
        var gate = new ManualTabletPressCompletionGate();

        gate.Arm();
        Assert.True(gate.TryCommit());
        gate.Arm();

        Assert.True(gate.TryCommit());
    }
}
