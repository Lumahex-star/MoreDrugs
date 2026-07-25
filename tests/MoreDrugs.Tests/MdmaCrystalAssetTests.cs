using System.Text;
using System.Text.Json;

namespace MoreDrugs.Tests;

public sealed class MdmaCrystalAssetTests
{
    private static readonly string[] RequiredVariants =
    {
        "CrystalPile",
        "CrystalChunk_A",
        "CrystalChunk_B",
        "CrystalGranules",
    };

    [Fact]
    public void GlbPreservesSemanticVariantContract()
    {
        string path =
            Path.Combine(
                AppContext.BaseDirectory,
                "Assets",
                "mdma_crystals.glb");
        using FileStream stream = File.OpenRead(path);
        using var reader =
            new BinaryReader(stream, Encoding.UTF8, leaveOpen: false);

        Assert.Equal(0x46546C67u, reader.ReadUInt32());
        Assert.Equal(2u, reader.ReadUInt32());
        Assert.Equal(checked((uint)stream.Length), reader.ReadUInt32());

        uint jsonLength = reader.ReadUInt32();
        Assert.Equal(0x4E4F534Au, reader.ReadUInt32());
        using JsonDocument document =
            JsonDocument.Parse(reader.ReadBytes(checked((int)jsonLength)));

        JsonElement[] nodes =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .ToArray();
        string[] nodeNames =
            nodes
                .Select(node => node.GetProperty("name").GetString()!)
                .ToArray();
        Assert.Equal(nodeNames.Length, nodeNames.Distinct().Count());

        int rootIndex =
            Array.FindIndex(
                nodeNames,
                name => string.Equals(
                    name,
                    "MdmaCrystals",
                    StringComparison.Ordinal));
        Assert.True(rootIndex >= 0);

        string[] childNames =
            nodes[rootIndex]
                .GetProperty("children")
                .EnumerateArray()
                .Select(index => nodeNames[index.GetInt32()])
                .Order(StringComparer.Ordinal)
                .ToArray();
        Assert.Equal(
            RequiredVariants.Order(StringComparer.Ordinal),
            childNames);

        string[] meshNodeNames =
            nodes
                .Where(node => node.TryGetProperty("mesh", out _))
                .Select(node => node.GetProperty("name").GetString()!)
                .Order(StringComparer.Ordinal)
                .ToArray();
        Assert.Equal(
            RequiredVariants.Order(StringComparer.Ordinal),
            meshNodeNames);
        Assert.False(document.RootElement.TryGetProperty("animations", out _));
    }
}
