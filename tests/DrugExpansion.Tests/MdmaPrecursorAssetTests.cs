using System.Text;
using System.Text.Json;

namespace DrugExpansion.Tests;

public sealed class MdmaPrecursorAssetTests
{
    [Fact]
    public void SafroleGlbPreservesVariantAndBudgetContract()
    {
        using JsonDocument document = ReadGlb("safrole.glb");

        AssertNodes(
            document,
            "SafroleRoot",
            "SafroleBottle",
            "SafroleCap",
            "SafroleNeckRing",
            "SafroleLiquid",
            "SafroleLiquidVolume",
            "SafrolePourPoint",
            "SafroleLabel_Low",
            "SafroleLabel_Standard",
            "SafroleLabel_High");
        AssertMaterialAlphaMode(
            document,
            "Safrole_AmberGlass",
            "BLEND");
        AssertMaterialAlphaMode(
            document,
            "Safrole_ClearLiquid",
            "BLEND");
        AssertMaterialBaseColor(
            document,
            "Safrole_ClearLiquid",
            new[] { 0.94f, 0.97f, 1f, 0.34f });
        AssertPourPointOrientation(document, "SafrolePourPoint");
        AssertOpenMouth(document, "SafroleNeckRing");
        Assert.InRange(MaterialCount(document), 1, 6);
        Assert.InRange(TriangleCount(document), 1, 2_500);
        Assert.False(
            document.RootElement.TryGetProperty("animations", out _));
    }

    [Fact]
    public void MethylamineGlbPreservesSemanticAndBudgetContract()
    {
        using JsonDocument document = ReadGlb("methylamine.glb");

        AssertNodes(
            document,
            "MethylamineRoot",
            "MethylamineJug",
            "MethylamineShoulder",
            "MethylamineNeck",
            "MethylamineCap",
            "MethylamineHandle",
            "MethylamineLabel",
            "MethylamineLiquidWindow",
            "MethylamineLiquidVolume",
            "MethylaminePourPoint",
            "MethylamineBase");
        AssertMaterialAlphaMode(
            document,
            "Methylamine_ClearLiquid",
            "BLEND");
        AssertMaterialBaseColor(
            document,
            "Methylamine_ClearLiquid",
            new[] { 0.94f, 0.97f, 1f, 0.34f });
        AssertPourPointOrientation(
            document,
            "MethylaminePourPoint");
        AssertOpenMouth(document, "MethylamineNeck");
        AssertNodeTranslation(
            document,
            "MethylamineLiquidVolume",
            axis: 1,
            expected: -0.008f,
            tolerance: 0.0001f);
        Assert.InRange(MaterialCount(document), 1, 6);
        Assert.InRange(TriangleCount(document), 1, 3_200);
        Assert.False(
            document.RootElement.TryGetProperty("animations", out _));
    }

    [Fact]
    public void DiscoDaveyGlbContainsOnlyOriginalSlingBag()
    {
        using JsonDocument document =
            ReadGlb("disco_davey_accessories.glb");

        string[] expected =
        {
            "FestivalSlingBag",
        };
        string[] nodeNames =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Select(node =>
                    node.GetProperty("name").GetString()!)
                .OrderBy(name => name, StringComparer.Ordinal)
                .ToArray();
        string[] meshNames =
            document.RootElement
                .GetProperty("meshes")
                .EnumerateArray()
                .Select(mesh =>
                    mesh.GetProperty("name").GetString()!)
                .OrderBy(name => name, StringComparer.Ordinal)
                .ToArray();
        string[] expectedMeshNames =
            expected.Select(name => $"{name}_Mesh").ToArray();

        Assert.Equal(expected, nodeNames);
        Assert.Equal(expectedMeshNames, meshNames);
        Assert.Equal(5, MaterialCount(document));
        Assert.InRange(TriangleCount(document), 1, 2_800);
        Assert.False(document.RootElement.TryGetProperty("skins", out _));
        Assert.False(
            document.RootElement.TryGetProperty("animations", out _));
    }

    [Theory]
    [InlineData("disco_davey_sneakers.png", 1024, 1024)]
    [InlineData("disco_davey_rave_jacket.png", 2048, 2048)]
    public void DiscoDaveyTexturesPreserveNativeUvCanvas(
        string fileName,
        int expectedWidth,
        int expectedHeight)
    {
        string path =
            Path.Combine(
                AppContext.BaseDirectory,
                "Assets",
                fileName);
        using FileStream stream = File.OpenRead(path);
        using var reader =
            new BinaryReader(stream, Encoding.UTF8, leaveOpen: false);

        Assert.Equal(
            new byte[]
            {
                137, 80, 78, 71, 13, 10, 26, 10,
            },
            reader.ReadBytes(8));
        Assert.Equal(13, ReadBigEndianInt32(reader));
        Assert.Equal("IHDR", Encoding.ASCII.GetString(reader.ReadBytes(4)));
        Assert.Equal(expectedWidth, ReadBigEndianInt32(reader));
        Assert.Equal(expectedHeight, ReadBigEndianInt32(reader));
        Assert.InRange(stream.Length, 1, 4 * 1024 * 1024);
    }

    private static JsonDocument ReadGlb(string fileName)
    {
        string path =
            Path.Combine(
                AppContext.BaseDirectory,
                "Assets",
                fileName);
        using FileStream stream = File.OpenRead(path);
        using var reader =
            new BinaryReader(stream, Encoding.UTF8, leaveOpen: false);

        Assert.Equal(0x46546C67u, reader.ReadUInt32());
        Assert.Equal(2u, reader.ReadUInt32());
        Assert.Equal(checked((uint)stream.Length), reader.ReadUInt32());

        uint jsonLength = reader.ReadUInt32();
        Assert.Equal(0x4E4F534Au, reader.ReadUInt32());
        return JsonDocument.Parse(
            reader.ReadBytes(checked((int)jsonLength)));
    }

    private static void AssertNodes(
        JsonDocument document,
        params string[] requiredNames)
    {
        string[] names =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Select(node =>
                    node.GetProperty("name").GetString()!)
                .ToArray();

        Assert.Equal(names.Length, names.Distinct().Count());
        foreach (string requiredName in requiredNames)
            Assert.Contains(requiredName, names);
    }

    private static int MaterialCount(JsonDocument document) =>
        document.RootElement.TryGetProperty(
            "materials",
            out JsonElement materials)
            ? materials.GetArrayLength()
            : 0;

    private static void AssertMaterialAlphaMode(
        JsonDocument document,
        string materialName,
        string expectedMode)
    {
        JsonElement material =
            document.RootElement
                .GetProperty("materials")
                .EnumerateArray()
                .Single(candidate =>
                    string.Equals(
                        candidate.GetProperty("name").GetString(),
                        materialName,
                        StringComparison.Ordinal));

        Assert.Equal(
            expectedMode,
            material.GetProperty("alphaMode").GetString());
    }

    private static void AssertMaterialBaseColor(
        JsonDocument document,
        string materialName,
        IReadOnlyList<float> expected)
    {
        JsonElement material =
            document.RootElement
                .GetProperty("materials")
                .EnumerateArray()
                .Single(candidate =>
                    string.Equals(
                        candidate.GetProperty("name").GetString(),
                        materialName,
                        StringComparison.Ordinal));
        JsonElement actual =
            material.GetProperty("pbrMetallicRoughness")
                .GetProperty("baseColorFactor");

        Assert.Equal(4, expected.Count);
        for (int index = 0; index < expected.Count; index++)
        {
            Assert.InRange(
                actual[index].GetSingle(),
                expected[index] - 0.001f,
                expected[index] + 0.001f);
        }
    }

    private static void AssertPourPointOrientation(
        JsonDocument document,
        string nodeName)
    {
        JsonElement node =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Single(candidate =>
                    string.Equals(
                        candidate.GetProperty("name").GetString(),
                        nodeName,
                        StringComparison.Ordinal));
        JsonElement rotation = node.GetProperty("rotation");

        Assert.InRange(rotation[0].GetSingle(), -0.708f, -0.706f);
        Assert.InRange(rotation[1].GetSingle(), -0.001f, 0.001f);
        Assert.InRange(rotation[2].GetSingle(), -0.001f, 0.001f);
        Assert.InRange(rotation[3].GetSingle(), 0.706f, 0.708f);
    }

    private static void AssertOpenMouth(
        JsonDocument document,
        string nodeName)
    {
        JsonElement node =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Single(candidate =>
                    string.Equals(
                        candidate.GetProperty("name").GetString(),
                        nodeName,
                        StringComparison.Ordinal));

        Assert.True(
            node.GetProperty("extras")
                .GetProperty("station_open_mouth")
                .GetBoolean());
    }

    private static void AssertNodeTranslation(
        JsonDocument document,
        string nodeName,
        int axis,
        float expected,
        float tolerance)
    {
        JsonElement node =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Single(candidate =>
                    string.Equals(
                        candidate.GetProperty("name").GetString(),
                        nodeName,
                        StringComparison.Ordinal));
        float value = node.GetProperty("translation")[axis].GetSingle();

        Assert.InRange(value, expected - tolerance, expected + tolerance);
    }

    private static int TriangleCount(JsonDocument document)
    {
        JsonElement accessors =
            document.RootElement.GetProperty("accessors");
        int indices = 0;
        foreach (JsonElement mesh in
                 document.RootElement
                     .GetProperty("meshes")
                     .EnumerateArray())
        {
            foreach (JsonElement primitive in
                     mesh.GetProperty("primitives").EnumerateArray())
            {
                int accessorIndex =
                    primitive.GetProperty("indices").GetInt32();
                indices +=
                    accessors[accessorIndex]
                        .GetProperty("count")
                        .GetInt32();
            }
        }

        Assert.Equal(0, indices % 3);
        return indices / 3;
    }

    private static int ReadBigEndianInt32(BinaryReader reader)
    {
        byte[] bytes = reader.ReadBytes(4);
        Assert.Equal(4, bytes.Length);
        return
            bytes[0] << 24 |
            bytes[1] << 16 |
            bytes[2] << 8 |
            bytes[3];
    }
}
