#if IL2CPPMELON
using Il2CppInterop.Runtime.InteropTypes;
using S1 = Il2CppScheduleOne;
using S1Product = Il2CppScheduleOne.Product;
#elif MONOMELON
using S1 = ScheduleOne;
using S1Product = ScheduleOne.Product;
#endif

using MelonLoader;
using MoreDrugs.Content.Mdma.Production;
using MoreDrugs.Infrastructure;
using S1API.Console;
using S1API.Items;
using S1API.Items.Buildable;
using S1API.Products;
using S1API.Properties;
using S1API.Rendering;
using S1API.Shops;
using S1API.Stations;
using S1API.Utils;
using UnityEngine;

namespace MoreDrugs.Content.Mdma;

internal sealed class MdmaModule : IDrugContentModule, IMixingCapability
{
    internal const string ProductKindId = "ifbars.moredrugs:mdma";
    internal const string ProductId = MdmaProductIds.Tablets;
    internal const string RecipeId = "ifbars.moredrugs:mdma-synthesis";
    internal const string ProviderData = "mdma";
    internal const string TabletPressItemId =
        "ifbars.moredrugs:stations/manual-tablet-press";

    private const string HeartPillResource =
        "MoreDrugs.Assets.Models.heartpill.glb";
    private const string MdmaCrystalsResource =
        "MoreDrugs.Assets.Models.mdma_crystals.glb";
    private const string TabletPressIconResource =
        "MoreDrugs.Assets.Icons.manual_tablet_press.png";

    private readonly MelonLogger.Instance _logger;
    private readonly EmbeddedGlbAsset _heartPill =
        new EmbeddedGlbAsset(HeartPillResource, "MoreDrugs_HeartPill");
    private readonly EmbeddedGlbAsset _mdmaCrystals =
        new EmbeddedGlbAsset(MdmaCrystalsResource, "MoreDrugs_MdmaCrystals");
    private readonly ManualTabletPressAsset _tabletPressAsset = new();

    private ProductKind? _productKind;
    private ProductPresentationProfile? _presentationProfile;
    private ProductPresentationProfile? _crystalPresentationProfile;
    private ProductPackagingContentProfile? _baggieProfile;
    private ProductPackagingContentProfile? _jarProfile;
    private ProductPackagingContentProfile? _crystalBaggieProfile;
    private ProductPackagingContentProfile? _crystalJarProfile;
    private CustomProductDefinition? _definition;
    private CustomProductDefinition? _crystalDefinition;
    private S1API.Items.Buildable.BuildableItemDefinition? _tabletPressDefinition;
    private ChemistryStationRecipe? _recipe;
    private ProductKindMetadata? _metadata;
    private ProductMixingProfile? _mixingProfile;
    private GameObject? _consumptionSource;
    private Sprite? _tabletPressIcon;
    private bool _tabletPressAddedToShop;
    private bool _tabletPressIconGenerated;

    internal MdmaModule(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    public string ProviderDataKey => ProviderData;

    public void RegisterContent()
    {
        if (_definition != null &&
            _crystalDefinition != null &&
            _tabletPressDefinition != null)
            return;

        ProductDefinition template =
            ItemManager.GetDefinition("cocaine") as ProductDefinition ??
            throw new InvalidOperationException(
                "The native 'cocaine' product scaffold is unavailable.");
        PackagingDefinition baggie =
            ItemManager.GetDefinition("baggie") as PackagingDefinition ??
            throw new InvalidOperationException(
                "The native 'baggie' packaging definition is unavailable.");
        PackagingDefinition jar =
            ItemManager.GetDefinition("jar") as PackagingDefinition ??
            throw new InvalidOperationException(
                "The native 'jar' packaging definition is unavailable.");

        _productKind ??=
            new ProductKindBuilder(ProductKindId)
                // Native product saves currently require a compatibility value. This is
                // metadata, not MDMA's logical identity or its mixing capability.
                .WithCompatibilityDrugType(DrugType.MDMA)
                .Build();

        GameObject pillSource = _heartPill.GetOrLoad();
        GameObject crystalSource = _mdmaCrystals.GetOrLoad();
        EnsurePresentationRegistered(template, pillSource);
        EnsureCrystalPresentationRegistered(crystalSource);
        EnsurePackagingRegistered(pillSource);
        EnsureCrystalPackagingRegistered(crystalSource);
        RegisterMixing(_productKind);

        _definition = CreateBuilder(template, baggie, jar).Build();
        _crystalDefinition = CreateCrystalBuilder(template, baggie, jar).Build();
        _tabletPressIcon ??=
            ImageUtils.LoadImageFromResource(
                typeof(MdmaModule).Assembly,
                TabletPressIconResource);
        S1API.Items.Buildable.BuildableItemDefinitionBuilder tabletPressBuilder =
            S1API.Items.Buildable.BuildableItemCreator.CloneFrom("brickpress")
                .WithBasicInfo(
                    TabletPressItemId,
                    "Manual Tablet Press",
                    "A hand-operated press for converting MDMA crystals into tablets.",
                    ItemCategory.Equipment)
                .WithBuildSound(S1API.Items.Buildable.BuildSoundType.Metal)
                .WithPricing(2_500f, 0.5f);
        if (_tabletPressIcon != null)
        {
            tabletPressBuilder.WithIcon(_tabletPressIcon);
            _tabletPressIconGenerated = true;
        }
        _tabletPressDefinition = tabletPressBuilder.Build();

        ConsoleItemAliases.Register("mdma", MdmaProductIds.Tablets);
        ConsoleItemAliases.Register("mdmacrystals", MdmaProductIds.Crystals);
        ConsoleItemAliases.Register("tabletpress", TabletPressItemId);
        ManualTabletPressRuntime.Configure(
            _tabletPressAsset,
            () => _heartPill.GetOrLoad(),
            () => _mdmaCrystals.GetOrLoad(),
            _logger);

        _recipe ??=
            ChemistryStationRecipes.CreateAndRegister(builder => builder
                .WithRecipeId(RecipeId)
                // StationRecipeEntry appends "(20x)" without a separator. The word
                // joiner preserves the preceding display space through S1API's trim.
                .WithTitle("MDMA Crystals \u2060")
                .WithCookTimeMinutes(240)
                .WithTemperature(220f, 20f)
                .WithFinalLiquidColor(new Color(0.95f, 0.3f, 0.65f))
                .WithIngredientOptions(
                    new[] { "lowqualitypseudo", "pseudo", "highqualitypseudo" },
                    2)
                .WithIngredient("acid", 1)
                .WithIngredient("phosphorus", 1)
                .WithProduct(MdmaProductIds.Crystals, ManualTabletPressRuntime.BatchSize));

        _logger.Msg(
            $"Registered MDMA products '{MdmaProductIds.Crystals}' and " +
            $"'{MdmaProductIds.Tablets}', tablet press '{TabletPressItemId}', " +
            $"and chemistry recipe '{RecipeId}'.");
    }

    public void CompleteLoad()
    {
        if (_definition == null ||
            _crystalDefinition == null ||
            _tabletPressDefinition == null ||
            _productKind == null)
            return;

        if (_metadata == null)
        {
            Sprite icon = _definition.Icon;
            if (icon == null)
            {
                _logger.Warning(
                    "MDMA icon generation has not completed; Product Manager metadata will retry on the next load.");
                return;
            }

            _metadata =
                new ProductKindMetadataBuilder(_productKind)
                    .WithDisplayName("MDMA")
                    .WithColor(new Color(0.95f, 0.3f, 0.65f))
                    .WithIcon(icon)
                    .WithSortOrder(100)
                    .WithSearchAliases("ecstasy", "molly", "pill")
                    .WithProductManagerVisibility()
                    .Build();
        }

        _definition.Discover(listForSale: true);
        EnsureCrystalsRemainIntermediate();
        TryGenerateTabletPressIcon();

        if (!_tabletPressAddedToShop)
        {
            int shopCount = ShopManager.AddToShops(
                _tabletPressDefinition,
                2_500f,
                "Handy Hank's Hardware",
                "Dan's Hardware");
            _tabletPressAddedToShop = shopCount > 0;
            if (!_tabletPressAddedToShop)
            {
                _logger.Warning(
                    "The Manual Tablet Press could not be added to a hardware store yet; registration will retry after the next load.");
            }
        }
    }

    public CustomProductDefinitionBuilder? Restore(
        CustomProductSaveDescriptor descriptor)
    {
        bool isTablets = string.Equals(
            descriptor.ProductId,
            MdmaProductIds.Tablets,
            StringComparison.OrdinalIgnoreCase);
        bool isCrystals = string.Equals(
            descriptor.ProductId,
            MdmaProductIds.Crystals,
            StringComparison.OrdinalIgnoreCase);
        if (!isTablets && !isCrystals)
        {
            return null;
        }

        ProductDefinition template =
            ItemManager.GetDefinition("cocaine") as ProductDefinition ??
            throw new InvalidOperationException(
                "Cannot restore MDMA without the native cocaine product scaffold.");
        PackagingDefinition baggie =
            ItemManager.GetDefinition("baggie") as PackagingDefinition ??
            throw new InvalidOperationException(
                "Cannot restore MDMA without native baggie packaging.");
        PackagingDefinition jar =
            ItemManager.GetDefinition("jar") as PackagingDefinition ??
            throw new InvalidOperationException(
                "Cannot restore MDMA without native jar packaging.");

        _productKind ??=
            new ProductKindBuilder(ProductKindId)
                .WithCompatibilityDrugType(DrugType.MDMA)
                .Build();

        GameObject pillSource = _heartPill.GetOrLoad();
        GameObject crystalSource = _mdmaCrystals.GetOrLoad();
        EnsurePresentationRegistered(template, pillSource);
        EnsureCrystalPresentationRegistered(crystalSource);
        EnsurePackagingRegistered(pillSource);
        EnsureCrystalPackagingRegistered(crystalSource);
        return isTablets
            ? CreateBuilder(template, baggie, jar)
            : CreateCrystalBuilder(template, baggie, jar);
    }

    public void Dispose()
    {
        if (_consumptionSource != null)
            UnityEngine.Object.Destroy(_consumptionSource);

        _consumptionSource = null;
        ManualTabletPressRuntime.Reset();
        _tabletPressAsset.Dispose();
        _mdmaCrystals.Dispose();
        _heartPill.Dispose();
    }

    public void RegisterMixing(ProductKind productKind)
    {
        _mixingProfile ??=
            new ProductMixingProfileBuilder(productKind)
                .WithMixerMap(ProductMixingMap.Cocaine)
                .WithOutputFactoryCompatibility(
                    "ifbars.moredrugs:mixing/mdma",
                    version: 1)
                .WithOutputFactory(input =>
                    new ProductMixingOutputDefinition(
                        input.MixName,
                        input.SourceKind,
                        Math.Min(999f, input.SourcePrice + 10f)))
                .Build();
    }

    private CustomProductDefinitionBuilder CreateBuilder(
        ProductDefinition template,
        PackagingDefinition baggie,
        PackagingDefinition jar)
    {
        ProductKind kind = _productKind ??
            throw new InvalidOperationException("MDMA product kind is not registered.");

        return CustomProductItemCreator
            .CreateBuilder(ProductId, kind)
            .WithName("MDMA")
            .WithDescription("Heart-shaped MDMA tablets.")
            .WithProductPrice(180f)
            .WithProperties(Property.Energizing, Property.Focused)
            .WithLegalStatus(LegalStatus.Illegal)
            .WithBaseAddictiveness(0.35f)
            .WithDefaultQuality(Quality.Premium)
            .WithRepresentationsFrom(template)
            .WithValidPackaging(baggie, jar)
            .WithEffectDurations(playerSeconds: 180, npcSeconds: 240)
            .WithNativeMixerMap(ProductMixingMap.Cocaine)
            .WithSaveProvider(
                DrugCatalog.SaveProviderId,
                DrugCatalog.SaveProviderVersion,
                ProviderData);
    }

    private CustomProductDefinitionBuilder CreateCrystalBuilder(
        ProductDefinition template,
        PackagingDefinition baggie,
        PackagingDefinition jar)
    {
        ProductKind kind = _productKind ??
            throw new InvalidOperationException("MDMA product kind is not registered.");

        return CustomProductItemCreator
            .CreateBuilder(MdmaProductIds.Crystals, kind)
            .WithName("MDMA Crystals")
            .WithDescription(
                "An unpressed MDMA batch ready for the Manual Tablet Press.")
            .WithProductPrice(140f)
            .WithProperties(Property.Energizing, Property.Focused)
            .WithLegalStatus(LegalStatus.Illegal)
            .WithBaseAddictiveness(0.35f)
            .WithDefaultQuality(Quality.Premium)
            .WithRepresentationsFrom(template)
            .WithValidPackaging(baggie, jar)
            .WithEffectDurations(playerSeconds: 180, npcSeconds: 240)
            .WithNativeMixerMap(ProductMixingMap.Cocaine)
            .WithSaveProvider(
                DrugCatalog.SaveProviderId,
                DrugCatalog.SaveProviderVersion,
                ProviderData);
    }

    private void EnsurePresentationRegistered(
        ProductDefinition template,
        GameObject pillSource)
    {
        ProductPresentationTransform pillPose =
            new ProductPresentationTransform(
                Vector3.zero,
                (
                    Quaternion.Euler(78f, 0f, -8f) *
                    Quaternion.Euler(0f, 90f, 0f)
                ).eulerAngles,
                Vector3.one * 0.06f);
        ProductPresentationTransform heldPillPose =
            new ProductPresentationTransform(
                pillPose.LocalPosition,
                (
                    Quaternion.Euler(-90f, 0f, 0f) *
                    Quaternion.Euler(0f, -90f, 0f)
                ).eulerAngles,
                pillPose.LocalScale);

        _consumptionSource ??= CreateConsumptionSource(pillSource, pillPose);
        _presentationProfile ??=
            new ProductPresentationProfileBuilder()
                .WithLooseVisual(() => pillSource, pillPose)
                .WithHeldVisual(() => pillSource, heldPillPose)
                .WithGeneratedIconFromLooseVisual(
                    size: 512,
                    fitToCamera: true,
                    cameraFill: 0.78f)
                .WithConsumptionPrefab(() => _consumptionSource)
                .Require(
                    ProductPresentationContext.Loose,
                    ProductPresentationContext.Stored,
                    ProductPresentationContext.Held,
                    ProductPresentationContext.Station,
                    ProductPresentationContext.FunctionalProduct,
                    ProductPresentationContext.Icon,
                    ProductPresentationContext.Consumption)
                .Build();

        ProductPresentationProfileRegistry.RegisterForProduct(
            ModInfo.OwnerId,
            MdmaProductIds.Tablets,
            _presentationProfile);
    }

    private void EnsurePackagingRegistered(GameObject pillSource)
    {
        _baggieProfile ??=
            new ProductPackagingContentProfileBuilder()
                .WithContent(() => pillSource)
                .AddPlacement(
                    new ProductPresentationTransform(
                        new Vector3(0f, -0.002f, 0f),
                        new Vector3(78f, -70f, -8f),
                        Vector3.one * 0.05f))
                .Build();
        _jarProfile ??=
            new ProductPackagingContentProfileBuilder()
                .WithContent(() => pillSource)
                .AddPlacements(
                    JarPlacement(-0.04f, 0.02f, 12f),
                    JarPlacement(0f, 0.02f, -28f),
                    JarPlacement(0.04f, 0.02f, 38f),
                    JarPlacement(-0.035f, 0.06f, -18f),
                    JarPlacement(0.035f, 0.06f, 22f),
                    JarPlacement(-0.04f, 0.095f, 48f),
                    JarPlacement(0f, 0.095f, -42f),
                    JarPlacement(0.04f, 0.095f, 8f),
                    JarPlacement(-0.02f, 0.13f, 65f),
                    JarPlacement(0.025f, 0.13f, -62f))
                .Build();

        ProductPackagingContentProfileRegistry.Register(
            ModInfo.OwnerId,
            ProductId,
            "baggie",
            _baggieProfile);
        ProductPackagingContentProfileRegistry.Register(
            ModInfo.OwnerId,
            ProductId,
            "jar",
            _jarProfile);
    }

    private void EnsureCrystalPresentationRegistered(GameObject crystalSource)
    {
        ProductPresentationTransform loosePose =
            new ProductPresentationTransform(
                Vector3.zero,
                Vector3.zero,
                Vector3.one);
        ProductPresentationTransform heldPose =
            new ProductPresentationTransform(
                new Vector3(0f, 0f, 0.01f),
                new Vector3(18f, -10f, 12f),
                Vector3.one * 0.75f);

        _crystalPresentationProfile ??=
            new ProductPresentationProfileBuilder()
                .WithLooseVisual(() => crystalSource, loosePose)
                .WithHeldVisual(() => crystalSource, heldPose)
                .WithGeneratedIconFromLooseVisual(
                    size: 512,
                    fitToCamera: true,
                    cameraFill: 0.92f)
                .WithGeneratedIconTransform(
                    new ProductPresentationTransform(
                        Vector3.zero,
                        new Vector3(45f, 0f, 0f),
                        Vector3.one))
                .Require(
                    ProductPresentationContext.Loose,
                    ProductPresentationContext.Stored,
                    ProductPresentationContext.Held,
                    ProductPresentationContext.Station,
                    ProductPresentationContext.FunctionalProduct,
                    ProductPresentationContext.Icon)
                .Build();

        ProductPresentationProfileRegistry.RegisterForProduct(
            ModInfo.OwnerId,
            MdmaProductIds.Crystals,
            _crystalPresentationProfile);
    }

    private void EnsureCrystalPackagingRegistered(GameObject crystalSource)
    {
        _crystalBaggieProfile ??=
            new ProductPackagingContentProfileBuilder()
                .WithContent(() => crystalSource)
                .AddPlacement(
                    new ProductPresentationTransform(
                        new Vector3(0f, -0.004f, 0f),
                        Vector3.zero,
                        Vector3.one * 0.52f))
                .Build();
        _crystalJarProfile ??=
            new ProductPackagingContentProfileBuilder()
                .WithContent(() => crystalSource)
                .AddPlacement(
                    new ProductPresentationTransform(
                        new Vector3(0f, 0.035f, 0f),
                        new Vector3(0f, 18f, 0f),
                        Vector3.one * 0.58f))
                .Build();

        ProductPackagingContentProfileRegistry.Register(
            ModInfo.OwnerId,
            MdmaProductIds.Crystals,
            "baggie",
            _crystalBaggieProfile);
        ProductPackagingContentProfileRegistry.Register(
            ModInfo.OwnerId,
            MdmaProductIds.Crystals,
            "jar",
            _crystalJarProfile);
    }

    private static ProductPresentationTransform JarPlacement(
        float x,
        float y,
        float zRotation)
    {
        return new ProductPresentationTransform(
            new Vector3(x, y, 0f),
            new Vector3(78f, 0f, zRotation),
            Vector3.one * 0.04f);
    }

    private void TryGenerateTabletPressIcon()
    {
        if (_tabletPressIconGenerated || _tabletPressDefinition == null)
            return;

        GameObject? iconSource = null;
        try
        {
            iconSource = new GameObject("MoreDrugs_TabletPressIconSource");
            ManualTabletPressRig rig =
                _tabletPressAsset.CreateInstance(iconSource.transform);
            rig.FreshTabletAssembly.gameObject.SetActive(false);
            foreach (Transform child in
                     rig.Root.GetComponentsInChildren<Transform>(true))
            {
                if (child.name.StartsWith(
                        "FinishedTablet_",
                        StringComparison.Ordinal))
                {
                    child.gameObject.SetActive(false);
                }
            }

            Sprite? icon = IconFactory.GenerateIconSprite(
                rig.Root.transform,
                size: 512,
                bakeSkinnedMeshes: true,
                fitToCamera: true,
                cameraFill: 0.72f);
            if (icon == null)
            {
                _logger.Warning(
                    "Manual Tablet Press icon generation is not ready; the inherited Brick Press icon will be used until the next load.");
                return;
            }

            _tabletPressDefinition.Icon = icon;
            ShopManager.RefreshItemIcon(_tabletPressDefinition);
            _tabletPressIconGenerated = true;
        }
        catch (Exception exception)
        {
            _logger.Warning(
                $"Manual Tablet Press icon generation failed; the inherited Brick Press icon will be used: {exception.Message}");
        }
        finally
        {
            if (iconSource != null)
                UnityEngine.Object.Destroy(iconSource);
        }
    }

    private void EnsureCrystalsRemainIntermediate()
    {
        S1Product.ProductDefinition? nativeDefinition =
            GetNativeProductDefinition(MdmaProductIds.Crystals);
        if (nativeDefinition == null)
        {
            _logger.Warning(
                "MDMA crystals could not be removed from product discovery because their native definition is unavailable.");
            return;
        }

        bool removedFromListings =
            S1Product.ProductManager.ListedProducts.Remove(nativeDefinition);
        bool removedFromDiscovery =
            S1Product.ProductManager.DiscoveredProducts.Remove(nativeDefinition);
        if (removedFromListings || removedFromDiscovery)
        {
            _logger.Msg(
                "Migrated MDMA crystals to an unfinished production intermediate; they are no longer listed or shown in Product Manager.");
        }
    }

    private static GameObject CreateConsumptionSource(
        GameObject pillSource,
        ProductPresentationTransform pillPose)
    {
        S1Product.ProductDefinition nativeTemplate =
            GetNativeProductDefinition("cocaine") ??
            throw new InvalidOperationException(
                "Cannot create the MDMA consumption prefab without the native cocaine scaffold.");
        GameObject consumptionSource =
            UnityEngine.Object.Instantiate(
                nativeTemplate.ConsumeAnimation.gameObject);
        consumptionSource.name = "MoreDrugs_MDMA_Consumption";
        UnityEngine.Object.DontDestroyOnLoad(consumptionSource);
        consumptionSource.transform.position = new Vector3(0f, -20000f, 0f);

        GameObject consumePill = UnityEngine.Object.Instantiate(pillSource);
        consumePill.name = "MoreDrugs_MDMA_Consumption_Visual";
        consumePill.transform.SetParent(consumptionSource.transform, false);
        consumePill.transform.localPosition = pillPose.LocalPosition;
        consumePill.transform.localEulerAngles = pillPose.LocalEulerAngles;
        consumePill.transform.localScale = pillPose.LocalScale;
        consumePill.SetActive(true);
        consumptionSource.SetActive(true);
        return consumptionSource;
    }

    private static S1Product.ProductDefinition? GetNativeProductDefinition(
        string itemId)
    {
#if IL2CPPMELON
        return S1.Registry.GetItem(itemId)?.TryCast<S1Product.ProductDefinition>();
#else
        return S1.Registry.GetItem(itemId) as S1Product.ProductDefinition;
#endif
    }
}
