#if IL2CPPMELON
using S1 = Il2CppScheduleOne;
using S1Product = Il2CppScheduleOne.Product;
#elif MONOMELON
using S1 = ScheduleOne;
using S1Product = ScheduleOne.Product;
#endif

using MelonLoader;
using MoreDrugs.Infrastructure;
using S1API.Items;
using S1API.Products;
using S1API.Properties;
using S1API.Stations;
using UnityEngine;

namespace MoreDrugs.Content.Mdma;

internal sealed class MdmaModule : IDrugContentModule, IMixingCapability
{
    internal const string ProductKindId = "ifbars.moredrugs:mdma";
    internal const string ProductId = "ifbars.moredrugs:products/mdma";
    internal const string RecipeId = "ifbars.moredrugs:mdma-synthesis";
    internal const string ProviderData = "mdma";

    private const string HeartPillResource =
        "MoreDrugs.Assets.Models.heartpill.glb";

    private readonly MelonLogger.Instance _logger;
    private readonly EmbeddedGlbAsset _heartPill =
        new EmbeddedGlbAsset(HeartPillResource, "MoreDrugs_HeartPill");

    private ProductKind? _productKind;
    private ProductPresentationProfile? _presentationProfile;
    private ProductPackagingContentProfile? _baggieProfile;
    private ProductPackagingContentProfile? _jarProfile;
    private CustomProductDefinition? _definition;
    private ChemistryStationRecipe? _recipe;
    private ProductKindMetadata? _metadata;
    private ProductMixingProfile? _mixingProfile;
    private GameObject? _consumptionSource;

    internal MdmaModule(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    public string ProviderDataKey => ProviderData;

    public void RegisterContent()
    {
        if (_definition != null)
            return;

        ProductDefinition template =
            ItemManager.GetDefinition("ogkush") as ProductDefinition ??
            ItemManager.GetDefinition("weed") as ProductDefinition ??
            throw new InvalidOperationException(
                "Neither 'ogkush' nor 'weed' is available as a native product scaffold.");
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
        EnsurePresentationRegistered(template, pillSource);
        EnsurePackagingRegistered(pillSource);
        RegisterMixing(_productKind);

        _definition = CreateBuilder(template, baggie, jar).Build();
        _recipe ??=
            ChemistryStationRecipes.CreateAndRegister(builder => builder
                .WithRecipeId(RecipeId)
                .WithTitle("Synthesize MDMA")
                .WithCookTimeMinutes(240)
                .WithTemperature(220f, 20f)
                .WithFinalLiquidColor(new Color(0.95f, 0.3f, 0.65f))
                .WithIngredientOptions(
                    new[] { "lowqualitypseudo", "pseudo", "highqualitypseudo" },
                    2)
                .WithIngredient("acid", 1)
                .WithIngredient("phosphorus", 1)
                .WithProduct(ProductId, 5));

        _logger.Msg(
            $"Registered MDMA product '{ProductId}' and chemistry recipe '{RecipeId}'.");
    }

    public void CompleteLoad()
    {
        if (_definition == null || _productKind == null)
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
    }

    public CustomProductDefinitionBuilder? Restore(
        CustomProductSaveDescriptor descriptor)
    {
        if (!string.Equals(
                descriptor.ProductId,
                ProductId,
                StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        ProductDefinition template =
            ItemManager.GetDefinition("ogkush") as ProductDefinition ??
            ItemManager.GetDefinition("weed") as ProductDefinition ??
            throw new InvalidOperationException(
                "Cannot restore MDMA without the native product scaffold.");
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
        EnsurePresentationRegistered(template, pillSource);
        EnsurePackagingRegistered(pillSource);
        return CreateBuilder(template, baggie, jar);
    }

    public void Dispose()
    {
        if (_consumptionSource != null)
            UnityEngine.Object.Destroy(_consumptionSource);

        _consumptionSource = null;
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

    private void EnsurePresentationRegistered(
        ProductDefinition template,
        GameObject pillSource)
    {
        ProductKind kind = _productKind ??
            throw new InvalidOperationException("MDMA product kind is not registered.");

        ProductPresentationTransform pillPose =
            new ProductPresentationTransform(
                Vector3.zero,
                (
                    Quaternion.Euler(78f, 0f, -8f) *
                    Quaternion.Euler(0f, 90f, 0f)
                ).eulerAngles,
                Vector3.one * 0.06f);

        _consumptionSource ??= CreateConsumptionSource(pillSource, pillPose);
        _presentationProfile ??=
            new ProductPresentationProfileBuilder()
                .WithLooseVisual(() => pillSource, pillPose)
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

        ProductPresentationProfileRegistry.RegisterForProductKind(
            ModInfo.OwnerId,
            kind,
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
        ProductPackagingContentProfileRegistry.RegisterForProductKind(
            ModInfo.OwnerId,
            ProductKindId,
            "baggie",
            _baggieProfile);
        ProductPackagingContentProfileRegistry.RegisterForProductKind(
            ModInfo.OwnerId,
            ProductKindId,
            "jar",
            _jarProfile);
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

    private static GameObject CreateConsumptionSource(
        GameObject pillSource,
        ProductPresentationTransform pillPose)
    {
        S1Product.ProductDefinition nativeTemplate =
            S1.Registry.GetItem("ogkush") as S1Product.ProductDefinition ??
            S1.Registry.GetItem("weed") as S1Product.ProductDefinition ??
            throw new InvalidOperationException(
                "Cannot create the MDMA consumption prefab without a native product scaffold.");
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
}
