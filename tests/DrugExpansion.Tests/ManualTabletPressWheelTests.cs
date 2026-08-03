using DrugExpansion.Content.Mdma.Production;

namespace DrugExpansion.Tests;

public sealed class ManualTabletPressWheelTests
{
    [Fact]
    public void ClockwiseQuarterTurnAdvancesProgress()
    {
        float degrees =
            ManualTabletPressWheel.AdvanceClockwise(0f, 0f, -90f);

        Assert.Equal(90f, degrees);
        Assert.Equal(
            1f / 12f,
            ManualTabletPressWheel.ToProgress(degrees),
            precision: 5);
    }

    [Fact]
    public void ClockwiseMotionAcrossAngleWrapAdvances()
    {
        float degrees =
            ManualTabletPressWheel.AdvanceClockwise(180f, -170f, 170f);

        Assert.Equal(200f, degrees);
    }

    [Fact]
    public void CounterClockwiseMotionReversesProgress()
    {
        float degrees =
            ManualTabletPressWheel.AdvanceClockwise(180f, 0f, 90f);

        Assert.Equal(90f, degrees);
    }

    [Theory]
    [InlineData(2000f, 0f, -90f, ManualTabletPressWheel.RequiredDegrees)]
    [InlineData(0f, 0f, 90f, 0f)]
    public void AccumulationStaysWithinPressCycle(
        float accumulated,
        float previousAngle,
        float currentAngle,
        float expected)
    {
        Assert.Equal(
            expected,
            ManualTabletPressWheel.AdvanceClockwise(
                accumulated,
                previousAngle,
                currentAngle));
    }
}
