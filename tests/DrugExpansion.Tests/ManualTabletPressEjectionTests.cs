using DrugExpansion.Content.Mdma.Production;

namespace DrugExpansion.Tests;

public sealed class ManualTabletPressEjectionTests
{
    [Fact]
    public void LiveOutputIncreaseAnimatesOnlyWhileStationIsInUse()
    {
        Assert.True(ManualTabletPressEjection.ShouldAnimate(0, 20, true));
        Assert.False(ManualTabletPressEjection.ShouldAnimate(0, 20, false));
        Assert.False(ManualTabletPressEjection.ShouldAnimate(20, 20, true));
        Assert.False(ManualTabletPressEjection.ShouldAnimate(20, 0, true));
        Assert.False(ManualTabletPressEjection.ShouldAnimate(-1, 20, true));
    }

    [Fact]
    public void DeterministicSequenceStaysNormalizedAndVariesPerTablet()
    {
        float[] firstPass =
            Enumerable.Range(0, 20)
                .Select(index => ManualTabletPressEjection.Unit((uint)index))
                .ToArray();
        float[] secondPass =
            Enumerable.Range(0, 20)
                .Select(index => ManualTabletPressEjection.Unit((uint)index))
                .ToArray();

        Assert.Equal(firstPass, secondPass);
        Assert.All(firstPass, value => Assert.InRange(value, 0f, 1f));
        Assert.True(firstPass.Distinct().Count() > 15);
    }

    [Fact]
    public void JitterStaysInsideRequestedAmplitude()
    {
        const float amplitude = 0.05f;
        for (uint sequence = 0; sequence < 100; sequence++)
        {
            Assert.InRange(
                ManualTabletPressEjection.Jitter(sequence, amplitude),
                -amplitude,
                amplitude);
        }
    }
}
