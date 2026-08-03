using MelonLoader;
using S1API.Entities;
using S1API.Entities.Appearances.AccessoryFields;
using S1API.Entities.Appearances.BodyLayerFields;
using S1API.Entities.Appearances.CustomizationFields;
using S1API.Entities.Appearances.FaceLayerFields;
using S1API.Entities.NPCs.Uptown;
using S1API.Entities.Voices;
using S1API.DeadDrops.Native;
using S1API.Map;
using UnityEngine;

namespace MoreDrugs.Content.Mdma.Precursors;

public sealed class DiscoDavey : NPC
{
    private static readonly Vector3 HiddenSpawnPosition =
        new(-50f, 1.06f, 70f);

    private static DiscoDavey? _activeInstance;
    private static bool _isAvailable;

    public new static string NPCId => MdmaPrecursorIds.DiscoDavey;

    public override bool IsPhysical => true;

    public override bool IsSupplier => true;

    internal static bool IsAvailable => _isAvailable;

    internal static bool IsRelationshipUnlocked =>
        _activeInstance?.Relationship.IsUnlocked ?? _isAvailable;

    internal static event Action<bool>? AvailabilityChanged;

    protected override void ConfigurePrefab(NPCPrefabBuilder builder)
    {
        builder
            .WithIdentity(NPCId, "Disco", "Davey")
            .WithVoice(NPCVoiceCatalog.Tyler, 0.94f)
            .WithAppearanceDefaults(appearance =>
            {
                appearance.Gender = 0.15f;
                appearance.Height = 1.02f;
                appearance.Weight = 0.45f;
                appearance.SkinColor =
                    new Color32(186, 139, 104, 255);
                appearance.LeftEyeLidColor = appearance.SkinColor;
                appearance.RightEyeLidColor = appearance.SkinColor;
                appearance.EyeBallTint = Color.white;
                appearance.PupilDilation = 0.82f;
                appearance.HairColor =
                    new Color32(18, 15, 18, 255);
                appearance.HairPath = HairStyle.Peaked;
                appearance.WithFaceLayer<Face>(
                    Face.SlightSmile,
                    Color.white);
                appearance.WithBodyLayer<Shirts>(
                    Shirts.TShirt,
                    Color.white);
                appearance.WithBodyLayer<Pants>(
                    Pants.Jeans,
                    new Color32(25, 25, 30, 255));
                appearance.WithAccessoryLayer<Head>(
                    Head.SmallRoundGlasses,
                    new Color32(139, 75, 222, 255));
                appearance.WithAccessoryLayer<Chest>(
                    DiscoDaveyAccessoryCatalog.RaveJacketPath,
                    Color.white);
                appearance.WithAccessoryLayer<Neck>(
                    Neck.GoldChain,
                    Color.white);
                appearance.WithAccessoryLayer<Feet>(
                    DiscoDaveyAccessoryCatalog.RecoloredSneakersPath,
                    Color.white);
                appearance.WithAccessoryLayer<Chest>(
                    DiscoDaveyAccessoryCatalog.FestivalSlingBagPath,
                    Color.white);

                appearance.WithImpostor("Benji");
            })
            .WithSpawnPosition(HiddenSpawnPosition)
            .EnsureSupplier()
            .WithSupplierDefaults(supplier => supplier
                .WithPersistentId(MdmaPrecursorIds.DiscoDaveyPersistentId)
                .WithOrderLimits(100f, 1_800f)
                .WithStashDeadDrop<BehindBank>()
                .WithDeliveryItem(MdmaPrecursorIds.SafroleLow)
                .WithDeliveryItem(MdmaPrecursorIds.SafroleStandard)
                .WithDeliveryItem(MdmaPrecursorIds.SafroleHigh)
                .WithDeliveryItem(MdmaPrecursorIds.Methylamine)
                .WithRecommendationMessage(
                    "Disco Davey always knows where the afterparty is - and where to find MDMA.")
                .WithUnlockHint(
                    "Disco Davey can now source MDMA. Check your messages before the next big night."))
            .WithRelationshipDefaults(relationship => relationship
                .WithDelta(0f)
                .SetUnlocked(false)
                .SetUnlockType(
                    NPCRelationship.UnlockType.Recommendation)
                .WithConnections<HerbertBleuball, TobiasWentworth>());
    }

    protected override void OnCreated()
    {
        try
        {
            base.OnCreated();
            _activeInstance = this;
            Region = Region.Uptown;
            Appearance.Build();

            Relationship.OnUnlocked -= HandleUnlocked;
            Relationship.OnUnlocked += HandleUnlocked;
            PublishAvailability(Relationship.IsUnlocked);
        }
        catch (Exception exception)
        {
            MelonLogger.Error(
                $"[MoreDrugs] Disco Davey initialization failed: {exception}");
        }
    }

    protected override void OnDestroyed()
    {
        Relationship.OnUnlocked -= HandleUnlocked;
        if (ReferenceEquals(_activeInstance, this))
            _activeInstance = null;
        PublishAvailability(false);
        base.OnDestroyed();
    }

    private void HandleUnlocked(
        NPCRelationship.UnlockType _,
        bool notify)
    {
        PublishAvailability(true);

        if (notify)
        {
            SendTextMessage(
                "Davey here. Herbert and Tobias say you're solid. Safrole, methylamine - whatever gets the night moving. Keep it quiet.");
        }
    }

    private static void PublishAvailability(bool available)
    {
        if (_isAvailable == available)
            return;

        _isAvailable = available;
        AvailabilityChanged?.Invoke(available);
    }
}
