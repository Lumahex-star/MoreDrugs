using MoreDrugs.Content.Mdma.Batch;

namespace MoreDrugs.Tests;

public sealed class MdmaBatchCodecTests
{
    [Fact]
    public void RoundTripPreservesAllFields()
    {
        var original = new MdmaBatchProfile(
            "0123456789abcdef0123456789abcdef",
            MdmaProductForm.Tablet,
            91,
            84,
            4,
            MdmaTestStatus.Verified,
            MdmaTabletColor.Purple,
            MdmaTabletImprint.Lightning,
            "Noche Ω");

        string payload = MdmaBatchCodec.Encode(original);
        bool decoded = MdmaBatchCodec.TryDecode(payload, out MdmaBatchProfile? restored);

        Assert.True(decoded);
        Assert.Equal(original, restored);
    }

    [Theory]
    [InlineData("")]
    [InlineData("2|0123456789abcdef0123456789abcdef|0|50|50|10|0|0|0|")]
    [InlineData("1|bad|0|50|50|10|0|0|0|")]
    [InlineData("1|0123456789abcdef0123456789abcdef|0|101|50|10|0|0|0|")]
    [InlineData("1|0123456789abcdef0123456789abcdef|0|50|50|10|0|1|0|")]
    [InlineData("1|0123456789abcdef0123456789abcdef|1|50|50|10|0|0|0|")]
    [InlineData("1|0123456789abcdef0123456789abcdef|1|50|50|10|0|1|1|%%%")]
    public void MalformedOrContradictoryPayloadIsRejected(string payload)
    {
        Assert.False(MdmaBatchCodec.TryDecode(payload, out _));
    }
}
