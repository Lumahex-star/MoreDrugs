using System.Text;
using System.Text.Json;

namespace DrugExpansion.Tests;

public sealed class ManualTabletPressAssetTests
{
    private static readonly string[] RequiredNodes =
    {
        "ManualTabletPress",
        "PedestalAssembly",
        "MachineAssembly",
        "HandlePivot",
        "RamAssembly",
        "FeedShoeAssembly",
        "FeedPowderAssembly",
        "DieFillAssembly",
        "EjectorAssembly",
        "FreshTabletAssembly",
        "CollectionTrayBed",
        "CollectionTrayOuterWall",
        "CollectionTrayFrontWall",
        "CollectionTrayRearWall",
        "CollectionTrayBridge",
        "HandleClickableAnchor",
        "PlaneNormal",
        "HandleRaised",
        "HandleLowered",
        "PressRaised",
        "PressLowered",
        "MouldDetector",
        "CameraPouring",
        "CameraPressing",
        "StandPoint",
        "ContainerSpawnPoint",
        "OutputPoint",
    };

    [Fact]
    public void GlbPreservesRuntimeContract()
    {
        string path =
            Path.Combine(
                AppContext.BaseDirectory,
                "Assets",
                "manual_tablet_press.glb");
        using FileStream stream = File.OpenRead(path);
        using var reader = new BinaryReader(stream, Encoding.UTF8, leaveOpen: false);

        Assert.Equal(0x46546C67u, reader.ReadUInt32());
        Assert.Equal(2u, reader.ReadUInt32());
        Assert.Equal(checked((uint)stream.Length), reader.ReadUInt32());

        uint jsonLength = reader.ReadUInt32();
        Assert.Equal(0x4E4F534Au, reader.ReadUInt32());
        using JsonDocument document =
            JsonDocument.Parse(reader.ReadBytes(checked((int)jsonLength)));

        string[] nodeNames =
            document.RootElement
                .GetProperty("nodes")
                .EnumerateArray()
                .Select(node => node.GetProperty("name").GetString()!)
                .ToArray();
        Assert.Equal(nodeNames.Length, nodeNames.Distinct().Count());
        foreach (string requiredNode in RequiredNodes)
            Assert.Contains(requiredNode, nodeNames);
        Assert.DoesNotContain("HopperBracket", nodeNames);

        JsonElement[] animations =
            document.RootElement
                .GetProperty("animations")
                .EnumerateArray()
                .ToArray();
        JsonElement animation = Assert.Single(animations);
        Assert.Equal("PressCycle", animation.GetProperty("name").GetString());

        string[] animatedNodes =
            animation
                .GetProperty("channels")
                .EnumerateArray()
                .Select(channel =>
                    nodeNames[
                        channel
                            .GetProperty("target")
                            .GetProperty("node")
                            .GetInt32()])
                .Distinct()
                .ToArray();
        Assert.Contains("HandlePivot", animatedNodes);
        Assert.Contains("RamAssembly", animatedNodes);
        Assert.Contains("FeedShoeAssembly", animatedNodes);
        Assert.Contains("FeedPowderAssembly", animatedNodes);
        Assert.Contains("DieFillAssembly", animatedNodes);
        Assert.Contains("EjectorAssembly", animatedNodes);
    }
}
