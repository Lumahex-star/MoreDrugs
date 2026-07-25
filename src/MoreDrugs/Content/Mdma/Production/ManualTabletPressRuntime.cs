#if IL2CPPMELON
using S1 = Il2CppScheduleOne;
using S1Building = Il2CppScheduleOne.Building;
using S1EntityFramework = Il2CppScheduleOne.EntityFramework;
using S1ItemFramework = Il2CppScheduleOne.ItemFramework;
using S1ObjectScripts = Il2CppScheduleOne.ObjectScripts;
using S1Product = Il2CppScheduleOne.Product;
using S1Tiles = Il2CppScheduleOne.Tiles;
using S1UIStations = Il2CppScheduleOne.UI.Stations;
using TmpText = Il2CppTMPro.TextMeshProUGUI;
#elif MONOMELON
using S1 = ScheduleOne;
using S1Building = ScheduleOne.Building;
using S1EntityFramework = ScheduleOne.EntityFramework;
using S1ItemFramework = ScheduleOne.ItemFramework;
using S1ObjectScripts = ScheduleOne.ObjectScripts;
using S1Product = ScheduleOne.Product;
using S1Tiles = ScheduleOne.Tiles;
using S1UIStations = ScheduleOne.UI.Stations;
using TmpText = TMPro.TextMeshProUGUI;
#endif

using System.Collections;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MelonLoader;
using MoreDrugs.Content.Mdma.Batch;
using UnityEngine;

namespace MoreDrugs.Content.Mdma.Production;

/// <summary>
/// Adapts the native Brick Press lifecycle for the MoreDrugs tablet press.
/// Inventory and slot replication remain native and authoritative; the authored
/// model and ejected rigidbodies are local presentation.
/// </summary>
internal static class ManualTabletPressRuntime
{
    internal const int BatchSize = 20;

    private static readonly ConditionalWeakTable<
        S1ObjectScripts.BrickPress,
        ManualTabletPressInstance> Instances = new();

    private static ManualTabletPressAsset? _pressAsset;
    private static Func<GameObject>? _pillSourceFactory;
    private static Func<GameObject>? _crystalSourceFactory;
    private static MelonLogger.Instance? _logger;

    internal static void Configure(
        ManualTabletPressAsset pressAsset,
        Func<GameObject> pillSourceFactory,
        Func<GameObject> crystalSourceFactory,
        MelonLogger.Instance logger)
    {
        _pressAsset = pressAsset ??
            throw new ArgumentNullException(nameof(pressAsset));
        _pillSourceFactory = pillSourceFactory ??
            throw new ArgumentNullException(nameof(pillSourceFactory));
        _crystalSourceFactory = crystalSourceFactory ??
            throw new ArgumentNullException(nameof(crystalSourceFactory));
        _logger = logger ??
            throw new ArgumentNullException(nameof(logger));
    }

    internal static void Reset()
    {
        _pressAsset = null;
        _pillSourceFactory = null;
        _crystalSourceFactory = null;
        _logger = null;
    }

    internal static bool IsTabletPress(S1ObjectScripts.BrickPress? press) =>
        press != null &&
        string.Equals(
            press.ItemInstance?.ID,
            MdmaModule.TabletPressItemId,
            StringComparison.OrdinalIgnoreCase);

    internal static bool IsTabletPressDefinition(
        S1ItemFramework.BuildableItemDefinition? definition) =>
        definition != null &&
        string.Equals(
            definition.ID,
            MdmaModule.TabletPressItemId,
            StringComparison.OrdinalIgnoreCase);

    internal static void Attach(S1ObjectScripts.BrickPress press)
    {
        if (!IsTabletPress(press) || Instances.TryGetValue(press, out _))
            return;

        if (_pressAsset == null ||
            _pillSourceFactory == null ||
            _crystalSourceFactory == null ||
            _logger == null)
        {
            MelonLogger.Warning(
                "Skipped Manual Tablet Press visuals because runtime assets are not configured.");
            return;
        }

        try
        {
            Instances.Add(
                press,
                new ManualTabletPressInstance(
                    press,
                    _pressAsset,
                    _pillSourceFactory,
                    _crystalSourceFactory));
        }
        catch (Exception exception)
        {
            _logger.Error(
                $"Failed to attach the Manual Tablet Press runtime: {exception}");
        }
    }

    internal static void AttachGhost(
        S1EntityFramework.GridItem ghost,
        S1ItemFramework.BuildableItemDefinition definition)
    {
        if (!IsTabletPressDefinition(definition) || _pressAsset == null)
            return;

        if (ghost.transform.Find("MoreDrugs_ManualTabletPress") != null)
            return;

        try
        {
            HideNativeRenderers(ghost.gameObject);
            ManualTabletPressRig rig = _pressAsset.CreateInstance(ghost.transform);
            DisableReferenceAnimation(rig.Root);
            DisableReferenceProcessVisuals(rig.Root);
        }
        catch (Exception exception)
        {
            _logger?.Error(
                $"Failed to create the Manual Tablet Press placement ghost: {exception}");
        }
    }

    internal static void Tick(S1ObjectScripts.BrickPress press)
    {
        if (Instances.TryGetValue(press, out ManualTabletPressInstance? instance))
            instance.Tick();
    }

    internal static bool TryGetSufficientCrystals(
        S1ObjectScripts.BrickPress press,
        out S1Product.ProductItemInstance? crystals)
    {
        crystals = null;
        int quantity = 0;

        foreach (S1ItemFramework.ItemSlot slot in press.InputSlots)
        {
            S1Product.ProductItemInstance? candidate =
                MdmaBatchRegistry.AsProduct(slot.ItemInstance);
            if (candidate == null ||
                !string.Equals(
                    candidate.ID,
                    MdmaProductIds.Crystals,
                    StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (crystals == null)
            {
                crystals = candidate;
            }
            else if (!crystals.CanStackWith(candidate, checkQuantities: false))
            {
                continue;
            }

            quantity += slot.Quantity;
            if (quantity >= BatchSize)
                return true;
        }

        crystals = null;
        return false;
    }

    internal static S1ObjectScripts.PackagingStation.EState GetState(
        S1ObjectScripts.BrickPress press)
    {
        if (!TryGetSufficientCrystals(press, out S1Product.ProductItemInstance? crystals) ||
            crystals == null)
        {
            return S1ObjectScripts.PackagingStation.EState.InsufficentProduct;
        }

        S1ItemFramework.ItemInstance? output = press.OutputSlot.ItemInstance;
        if (output == null)
            return S1ObjectScripts.PackagingStation.EState.CanBegin;

        S1Product.ProductItemInstance? outputProduct =
            MdmaBatchRegistry.AsProduct(output);
        if (outputProduct == null ||
            !string.Equals(
                outputProduct.ID,
                MdmaProductIds.Tablets,
                StringComparison.OrdinalIgnoreCase))
        {
            return S1ObjectScripts.PackagingStation.EState.Mismatch;
        }

        MdmaBatchProfile expected =
            MdmaBatchRegistry.GetOrCreate(crystals).Press(
                MdmaTabletColor.Pink,
                MdmaTabletImprint.Heart,
                string.Empty);
        if (!MdmaBatchRegistry.GetOrCreate(outputProduct).Equals(expected))
            return S1ObjectScripts.PackagingStation.EState.Mismatch;

        return output.Quantity + BatchSize <= output.StackLimit
            ? S1ObjectScripts.PackagingStation.EState.CanBegin
            : S1ObjectScripts.PackagingStation.EState.OutputSlotFull;
    }

    internal static bool CompletePress(
        S1ObjectScripts.BrickPress press,
        S1Product.ProductItemInstance crystals)
    {
        if (!IsTabletPress(press))
            return false;

        if (!TryGetSufficientCrystals(
                press,
                out S1Product.ProductItemInstance? authoritativeCrystals) ||
            authoritativeCrystals == null ||
            !authoritativeCrystals.CanStackWith(
                crystals,
                checkQuantities: false) ||
            GetState(press) != S1ObjectScripts.PackagingStation.EState.CanBegin)
        {
            _logger?.Warning(
                "Rejected a Manual Tablet Press completion because its replicated slots were no longer ready.");
            return true;
        }

        S1Product.ProductDefinition? tabletDefinition =
            GetNativeProductDefinition(MdmaProductIds.Tablets);
        if (tabletDefinition == null)
        {
            _logger?.Error(
                $"Cannot complete tablet pressing because '{MdmaProductIds.Tablets}' is not registered.");
            return true;
        }

        S1Product.ProductItemInstance? tablets =
            AsProduct(tabletDefinition.GetDefaultInstance(BatchSize));
        if (tablets == null)
        {
            _logger?.Error(
                "Cannot complete tablet pressing because the tablet definition did not create a product instance.");
            return true;
        }

        MdmaBatchProfile tabletProfile =
            MdmaBatchRegistry.GetOrCreate(authoritativeCrystals).Press(
                MdmaTabletColor.Pink,
                MdmaTabletImprint.Heart,
                string.Empty);
        MdmaBatchRegistry.Attach(tablets, tabletProfile);

        press.OutputSlot.AddItem(tablets);
        ConsumeCrystals(press, authoritativeCrystals);
        return true;
    }

    internal static void RefreshCanvas(S1UIStations.BrickPressCanvas canvas)
    {
        S1ObjectScripts.BrickPress? press = canvas.Press;
        bool isTabletPress = IsTabletPress(press);
        SetCanvasTitle(
            canvas,
            isTabletPress ? "Manual Tablet Press" : "Brick Press");
        if (!isTabletPress || press == null)
            return;

        switch (GetState(press))
        {
            case S1ObjectScripts.PackagingStation.EState.CanBegin:
                canvas.InstructionLabel.enabled = false;
                canvas.BeginButton.interactable = true;
                return;
            case S1ObjectScripts.PackagingStation.EState.InsufficentProduct:
                canvas.InstructionLabel.text =
                    $"Drag {BatchSize}x MDMA Crystals into input slots";
                break;
            case S1ObjectScripts.PackagingStation.EState.Mismatch:
                canvas.InstructionLabel.text =
                    "Output must contain matching MDMA tablets";
                break;
            default:
                canvas.InstructionLabel.text =
                    $"Output slot needs room for {BatchSize}x MDMA";
                break;
        }

        canvas.InstructionLabel.enabled = true;
        canvas.BeginButton.interactable = false;
    }

    private static void SetCanvasTitle(
        S1UIStations.BrickPressCanvas canvas,
        string title)
    {
        Transform? titleTransform =
            canvas.transform.Find("Container/Top/Title");
        TmpText? titleLabel =
            titleTransform?.GetComponent<TmpText>();
        if (titleLabel == null)
        {
            foreach (TmpText candidate in
                     canvas.GetComponentsInChildren<TmpText>(true))
            {
                if (string.Equals(
                        candidate.name,
                        "Title",
                        StringComparison.Ordinal))
                {
                    titleLabel = candidate;
                    break;
                }
            }
        }

        if (titleLabel != null)
            titleLabel.text = title;
    }

    private static void ConsumeCrystals(
        S1ObjectScripts.BrickPress press,
        S1Product.ProductItemInstance crystals)
    {
        int remaining = BatchSize;
        foreach (S1ItemFramework.ItemSlot slot in press.InputSlots)
        {
            if (remaining <= 0)
                break;

            S1Product.ProductItemInstance? candidate =
                MdmaBatchRegistry.AsProduct(slot.ItemInstance);
            if (candidate == null ||
                !candidate.CanStackWith(crystals, checkQuantities: false))
            {
                continue;
            }

            int consumed = Mathf.Min(remaining, slot.Quantity);
            slot.ChangeQuantity(-consumed);
            remaining -= consumed;
        }
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

    private static S1Product.ProductItemInstance? AsProduct(
        S1ItemFramework.ItemInstance? instance)
    {
#if IL2CPPMELON
        return instance?.TryCast<S1Product.ProductItemInstance>();
#else
        return instance as S1Product.ProductItemInstance;
#endif
    }

    private static void HideNativeRenderers(GameObject root)
    {
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
            renderer.enabled = false;
    }

    private static void DisableReferenceAnimation(GameObject root)
    {
        foreach (Component component in root.GetComponentsInChildren<Component>(true))
        {
            if (component is Behaviour behaviour &&
                string.Equals(
                    component.GetType().Name,
                    "Animator",
                    StringComparison.Ordinal))
            {
                behaviour.enabled = false;
            }
        }
    }

    private static void DisableReferenceProcessVisuals(GameObject root)
    {
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            if (transform.name.StartsWith(
                    "FinishedTablet_",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "FreshTabletAssembly",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "FeedPowderAssembly",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "DieFillAssembly",
                    StringComparison.Ordinal))
            {
                transform.gameObject.SetActive(false);
            }
        }
    }

    [HarmonyPatch(
        typeof(S1ObjectScripts.BrickPress),
        nameof(S1ObjectScripts.BrickPress.InitializeGridItem))]
    private static class InitializeGridItemPatch
    {
        private static void Postfix(S1ObjectScripts.BrickPress __instance) =>
            Attach(__instance);
    }

    [HarmonyPatch(typeof(S1ObjectScripts.BrickPress), "LateUpdate")]
    private static class LateUpdatePatch
    {
        private static void Postfix(S1ObjectScripts.BrickPress __instance) =>
            Tick(__instance);
    }

    [HarmonyPatch(
        typeof(S1ObjectScripts.BrickPress),
        nameof(S1ObjectScripts.BrickPress.HasSufficientProduct))]
    private static class HasSufficientProductPatch
    {
        private static bool Prefix(
            S1ObjectScripts.BrickPress __instance,
            ref S1Product.ProductItemInstance product,
            ref bool __result)
        {
            if (!IsTabletPress(__instance))
                return true;

            __result = TryGetSufficientCrystals(
                __instance,
                out S1Product.ProductItemInstance? crystals);
            product = crystals!;
            return false;
        }
    }

    [HarmonyPatch(
        typeof(S1ObjectScripts.BrickPress),
        nameof(S1ObjectScripts.BrickPress.GetState))]
    private static class GetStatePatch
    {
        private static bool Prefix(
            S1ObjectScripts.BrickPress __instance,
            ref S1ObjectScripts.PackagingStation.EState __result)
        {
            if (!IsTabletPress(__instance))
                return true;

            __result = GetState(__instance);
            return false;
        }
    }

    [HarmonyPatch(
        typeof(S1ObjectScripts.BrickPress),
        nameof(S1ObjectScripts.BrickPress.CompletePress))]
    private static class CompletePressPatch
    {
        private static bool Prefix(
            S1ObjectScripts.BrickPress __instance,
            S1Product.ProductItemInstance product) =>
            !CompletePress(__instance, product);
    }

    [HarmonyPatch(typeof(S1UIStations.BrickPressCanvas), "UpdateUI")]
    private static class CanvasUpdatePatch
    {
        private static void Postfix(S1UIStations.BrickPressCanvas __instance) =>
            RefreshCanvas(__instance);
    }

    [HarmonyPatch(typeof(S1Building.BuildStart_Grid), "CreateGhostModel")]
    private static class CreateGhostModelPatch
    {
        private static void Postfix(
            S1ItemFramework.BuildableItemDefinition itemDefinition,
            S1EntityFramework.GridItem __result)
        {
            if (__result != null)
                AttachGhost(__result, itemDefinition);
        }
    }
}

internal sealed class ManualTabletPressInstance
{
    private const int MaximumVisibleTablets = 20;
    private const float EjectionIntervalSeconds = 0.11f;
    private const float GuidedPathSeconds = 0.65f;

    private readonly S1ObjectScripts.BrickPress _press;
    private readonly Func<GameObject> _pillSourceFactory;
    private readonly ManualTabletPressRig _rig;
    private readonly GameObject _hopperCrystals;
    private readonly GameObject _shoeGranules;
    private readonly GameObject _dieGranules;
    private readonly Quaternion _handleHomeRotation;
    private readonly Vector3 _ramRaised;
    private readonly Vector3 _ramLowered;
    private readonly Vector3 _feedHome;
    private readonly Vector3 _feedAtDie;
    private readonly Vector3 _ejectorHome;
    private readonly List<GameObject> _tablets = new();

    private int _observedOutputQuantity = -1;
    private bool _ejectionRunning;
    private int _queuedEjections;
    private uint _sequence;

    internal ManualTabletPressInstance(
        S1ObjectScripts.BrickPress press,
        ManualTabletPressAsset asset,
        Func<GameObject> pillSourceFactory,
        Func<GameObject> crystalSourceFactory)
    {
        _press = press;
        _pillSourceFactory = pillSourceFactory;

        HideNativeRenderers(press.gameObject);
        _rig = asset.CreateInstance(press.transform);
        DisableReferenceAnimation(_rig.Root);
        DisableReferenceProcessVisuals(_rig.Root);
        GameObject crystalSource = crystalSourceFactory();
        _hopperCrystals =
            CreateCrystalVisual(
                crystalSource,
                "MoreDrugs_HopperCrystals",
                _rig.Root.transform,
                Require(_rig.Root, "PowderHopperRim"),
                0.75f,
                -0.009f,
                "CrystalPile",
                "CrystalChunk_A",
                "CrystalChunk_B");
        _shoeGranules =
            CreateCrystalVisual(
                crystalSource,
                "MoreDrugs_FeedGranules",
                _rig.FeedShoeAssembly,
                Require(_rig.Root, "FeedPowder"),
                0.58f,
                0.002f,
                "CrystalGranules");
        _dieGranules =
            CreateCrystalVisual(
                crystalSource,
                "MoreDrugs_DieGranules",
                _rig.Root.transform,
                Require(_rig.Root, "DiePowderFill"),
                0.52f,
                0.002f,
                "CrystalGranules");

        _handleHomeRotation = _rig.HandlePivot.localRotation;
        _ramRaised =
            _rig.RamAssembly.parent.InverseTransformPoint(_rig.PressRaised.position);
        _ramLowered =
            _rig.RamAssembly.parent.InverseTransformPoint(_rig.PressLowered.position);
        _feedHome = _rig.FeedShoeAssembly.localPosition;
        Vector3 dieInFeedSpace =
            _rig.FeedShoeAssembly.parent.InverseTransformPoint(
                _rig.MouldDetector.position);
        _feedAtDie = new Vector3(
            dieInFeedSpace.x,
            _feedHome.y,
            _feedHome.z);
        _ejectorHome = _rig.EjectorAssembly.localPosition;

        ConfigureNativeInteraction();
        AddTrayColliders();
        ApplyMechanics(0f);
    }

    internal void Tick()
    {
        float progress = Mathf.Clamp01(_press.Handle.CurrentPosition);
        ApplyMechanics(progress);
        ObserveOutput();
    }

    private void ConfigureNativeInteraction()
    {
        Vector3 cameraFocus =
            _rig.MouldDetector.position +
            _rig.Root.transform.up * 0.16f;
        _rig.CameraPressing.LookAt(
            cameraFocus,
            _rig.Root.transform.up);
        _rig.CameraPouring.LookAt(
            _rig.MouldDetector.position +
            _rig.Root.transform.up * 0.08f,
            _rig.Root.transform.up);

        _press.CameraPosition = _rig.CameraPressing;
        _press.CameraPosition_Pouring = _rig.CameraPouring;
        _press.CameraPosition_Raising = _rig.CameraPressing;
        _press.StandPoint = _rig.StandPoint;
        _press.ContainerSpawnPoint = _rig.ContainerSpawnPoint;

        _press.Handle.PlaneNormal = _rig.PlaneNormal;
        _press.Handle.RaisedTransform = _rig.HandleRaised;
        _press.Handle.LoweredTransform = _rig.HandleLowered;

        Transform clickable = _press.Handle.HandleClickable.transform;
        clickable.position = _rig.HandleClickableAnchor.position;
        clickable.rotation = _rig.HandleClickableAnchor.rotation;

        Transform mould = _press.MouldDetection.transform;
        mould.position = _rig.MouldDetector.position;
        mould.rotation = _rig.MouldDetector.rotation;
        _press.MouldDetection.size = new Vector3(0.28f, 0.18f, 0.28f);

        if (_press.OutputVisuals != null)
            _press.OutputVisuals.enabled = false;
    }

    private void ApplyMechanics(float progress)
    {
        _rig.HandlePivot.localRotation =
            _handleHomeRotation *
            Quaternion.AngleAxis(360f * progress, Vector3.forward);
        _rig.RamAssembly.localPosition =
            Vector3.Lerp(_ramRaised, _ramLowered, progress);
        float ejectProgress =
            progress <= 0.82f
                ? 0f
                : Mathf.SmoothStep(0f, 1f, (progress - 0.82f) / 0.18f);
        _rig.EjectorAssembly.localPosition =
            _ejectorHome + Vector3.up * (0.10f * ejectProgress);

        bool hasCrystals =
            ManualTabletPressRuntime.TryGetSufficientCrystals(
                _press,
                out _);
        float feedProgress =
            progress <= 0.30f
                ? Mathf.SmoothStep(0f, 1f, progress / 0.30f)
                : progress >= 0.55f
                    ? Mathf.SmoothStep(1f, 0f, (progress - 0.55f) / 0.35f)
                    : 1f;
        _rig.FeedShoeAssembly.localPosition =
            Vector3.Lerp(_feedHome, _feedAtDie, feedProgress);

        bool powderInShoe = hasCrystals && progress < 0.28f;
        bool powderInDie =
            hasCrystals &&
            progress >= 0.28f &&
            progress < 0.82f;
        _hopperCrystals.SetActive(hasCrystals);
        _shoeGranules.SetActive(powderInShoe);
        _dieGranules.SetActive(powderInDie);
    }

    private void ObserveOutput()
    {
        int outputQuantity = GetOutputQuantity();
        if (_observedOutputQuantity < 0)
        {
            _observedOutputQuantity = outputQuantity;
            RebuildSettledTablets(outputQuantity);
            return;
        }

        if (outputQuantity == _observedOutputQuantity)
            return;

        int delta = outputQuantity - _observedOutputQuantity;
        _observedOutputQuantity = outputQuantity;
        bool stationInUse =
            _press.PlayerUserObject != null ||
            _press.NPCUserObject != null;
        if (ManualTabletPressEjection.ShouldAnimate(
                outputQuantity - delta,
                outputQuantity,
                stationInUse))
        {
            QueueEjections(delta);
        }
        else
        {
            RebuildSettledTablets(outputQuantity);
        }
    }

    private int GetOutputQuantity()
    {
        S1ItemFramework.ItemInstance? output = _press.OutputSlot?.ItemInstance;
        return output != null &&
               string.Equals(
                   output.ID,
                   MdmaProductIds.Tablets,
                   StringComparison.OrdinalIgnoreCase)
            ? output.Quantity
            : 0;
    }

    private void QueueEjections(int count)
    {
        _queuedEjections += Math.Min(count, MaximumVisibleTablets);
        if (_ejectionRunning)
            return;

        _ejectionRunning = true;
        MelonCoroutines.Start(EjectQueuedTablets());
    }

    private IEnumerator EjectQueuedTablets()
    {
        while (_queuedEjections > 0)
        {
            _queuedEjections--;
            if (_tablets.Count >= MaximumVisibleTablets)
                DestroyTabletAt(0);

            yield return AnimateOneTablet(_sequence++);
            if (_queuedEjections > 0)
                yield return new WaitForSeconds(EjectionIntervalSeconds);
        }

        _ejectionRunning = false;
    }

    private IEnumerator AnimateOneTablet(uint sequence)
    {
        GameObject tablet = CreateTabletVisual();
        _tablets.Add(tablet);

        Vector3 start =
            _rig.FreshTabletAssembly.position +
            _rig.EjectorAssembly.parent.TransformVector(Vector3.up * 0.10f);
        Vector3 end =
            _rig.OutputPoint.position +
            _press.transform.up * 0.12f +
            _press.transform.right *
                ManualTabletPressEjection.Jitter(sequence, 0.025f) +
            _press.transform.forward *
                ManualTabletPressEjection.Jitter(sequence + 11u, 0.05f);
        Vector3 control =
            Vector3.Lerp(start, end, 0.48f) +
            _press.transform.up * 0.18f;

        Quaternion startRotation =
            _press.transform.rotation * Quaternion.Euler(0f, 0f, -10f);
        Quaternion endRotation =
            _press.transform.rotation *
            Quaternion.Euler(
                78f,
                ManualTabletPressEjection.Unit(sequence + 23u) * 120f - 60f,
                -8f);

        float elapsed = 0f;
        while (elapsed < GuidedPathSeconds && tablet != null)
        {
            elapsed += Time.deltaTime;
            float t = Mathf.Clamp01(elapsed / GuidedPathSeconds);
            float eased = Mathf.SmoothStep(0f, 1f, t);
            tablet.transform.position =
                QuadraticBezier(start, control, end, eased);
            tablet.transform.rotation =
                Quaternion.Slerp(startRotation, endRotation, eased);
            yield return null;
        }

        if (tablet == null)
            yield break;

        Rigidbody body = tablet.AddComponent<Rigidbody>();
        body.mass = 0.02f;
        body.drag = 0.18f;
        body.angularDrag = 0.28f;
        body.interpolation = RigidbodyInterpolation.Interpolate;
        body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        body.velocity =
            _press.transform.right *
                (0.08f +
                 ManualTabletPressEjection.Unit(sequence + 31u) * 0.08f) +
            _press.transform.forward *
                ManualTabletPressEjection.Jitter(sequence + 47u, 0.09f) -
            _press.transform.up * 0.04f;
        body.angularVelocity = new Vector3(
            ManualTabletPressEjection.Jitter(sequence + 59u, 2.4f),
            ManualTabletPressEjection.Jitter(sequence + 71u, 2.4f),
            ManualTabletPressEjection.Jitter(sequence + 83u, 2.4f));
    }

    private GameObject CreateTabletVisual()
    {
        GameObject source = _pillSourceFactory();
        GameObject tablet = UnityEngine.Object.Instantiate(source);
        tablet.name = "MoreDrugs_EjectedTablet";
        tablet.transform.SetParent(_rig.Root.transform, true);
        tablet.transform.localScale = Vector3.one * 0.045f;
        tablet.layer = LayerMask.NameToLayer("Ignore Raycast");
        tablet.SetActive(true);

        foreach (Collider collider in tablet.GetComponentsInChildren<Collider>(true))
            UnityEngine.Object.Destroy(collider);
        AddTabletCollider(tablet);
        return tablet;
    }

    private GameObject CreateCrystalVisual(
        GameObject source,
        string name,
        Transform visualParent,
        Transform anchor,
        float scale,
        float verticalOffset,
        params string[] visibleVariants)
    {
        var visible = new HashSet<string>(
            visibleVariants,
            StringComparer.Ordinal);
        GameObject visual = UnityEngine.Object.Instantiate(source);
        visual.name = name;
        visual.transform.SetParent(visualParent, false);
        visual.transform.position =
            anchor.position + _rig.Root.transform.up * verticalOffset;
        visual.transform.rotation = _rig.Root.transform.rotation;
        visual.transform.localScale = Vector3.one * scale;
        visual.layer = LayerMask.NameToLayer("Ignore Raycast");

        var found = new HashSet<string>(StringComparer.Ordinal);
        foreach (Transform transform in
                 visual.GetComponentsInChildren<Transform>(true))
        {
            if (!IsCrystalVariant(transform.name))
                continue;

            bool enabled = visible.Contains(transform.name);
            transform.gameObject.SetActive(enabled);
            if (enabled)
                found.Add(transform.name);
        }

        if (!found.SetEquals(visible))
        {
            UnityEngine.Object.Destroy(visual);
            throw new InvalidOperationException(
                $"The MDMA crystal model is missing variants: " +
                $"{string.Join(", ", visible.Except(found))}.");
        }

        foreach (Collider collider in
                 visual.GetComponentsInChildren<Collider>(true))
        {
            UnityEngine.Object.Destroy(collider);
        }

        visual.SetActive(false);
        return visual;
    }

    private void RebuildSettledTablets(int outputQuantity)
    {
        DestroyAllTablets();

        int count = Math.Min(outputQuantity, MaximumVisibleTablets);
        for (int index = 0; index < count; index++)
        {
            GameObject tablet = CreateTabletVisual();
            int row = index / 5;
            int column = index % 5;
            float x = (column - 2f) * 0.055f +
                      ManualTabletPressEjection.Jitter(
                          (uint)index + 3u,
                          0.012f);
            float z = (row - 1.5f) * 0.065f +
                      ManualTabletPressEjection.Jitter(
                          (uint)index + 17u,
                          0.012f);
            tablet.transform.position =
                _rig.OutputPoint.position +
                _press.transform.right * x +
                _press.transform.forward * z +
                _press.transform.up * (0.018f + row * 0.008f);
            tablet.transform.rotation =
                _press.transform.rotation *
                Quaternion.Euler(
                    78f,
                    ManualTabletPressEjection.Unit((uint)index + 29u) *
                        100f -
                    50f,
                    -8f);
            _tablets.Add(tablet);
        }
    }

    private void AddTrayColliders()
    {
        AddMeshColliderBox("CollectionTrayBed");
        AddMeshColliderBox("CollectionTrayOuterWall");
        AddMeshColliderBox("CollectionTrayFrontWall");
        AddMeshColliderBox("CollectionTrayRearWall");
        AddMeshColliderBox("CollectionTrayBridge");
    }

    private void AddMeshColliderBox(string nodeName)
    {
        Transform? node = Find(_rig.Root, nodeName);
        if (node == null || node.GetComponent<Collider>() != null)
            return;

        MeshFilter? filter = node.GetComponent<MeshFilter>();
        if (filter?.sharedMesh == null)
            return;

        BoxCollider collider = node.gameObject.AddComponent<BoxCollider>();
        collider.center = filter.sharedMesh.bounds.center;
        collider.size = filter.sharedMesh.bounds.size;
    }

    private static void AddTabletCollider(GameObject tablet)
    {
        Renderer[] renderers = tablet.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0)
            return;

        Bounds bounds = renderers[0].bounds;
        for (int index = 1; index < renderers.Length; index++)
            bounds.Encapsulate(renderers[index].bounds);

        Vector3 scale = tablet.transform.lossyScale;
        BoxCollider collider = tablet.AddComponent<BoxCollider>();
        collider.center = tablet.transform.InverseTransformPoint(bounds.center);
        collider.size = new Vector3(
            SafeDivide(bounds.size.x, scale.x),
            SafeDivide(bounds.size.y, scale.y),
            SafeDivide(bounds.size.z, scale.z));
    }

    private void DestroyAllTablets()
    {
        for (int index = _tablets.Count - 1; index >= 0; index--)
            DestroyTabletAt(index);
    }

    private void DestroyTabletAt(int index)
    {
        GameObject tablet = _tablets[index];
        _tablets.RemoveAt(index);
        if (tablet != null)
            UnityEngine.Object.Destroy(tablet);
    }

    private static Transform? Find(GameObject root, string name)
    {
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            if (string.Equals(transform.name, name, StringComparison.Ordinal))
                return transform;
        }

        return null;
    }

    private static Transform Require(GameObject root, string name) =>
        Find(root, name) ??
        throw new InvalidOperationException(
            $"The tablet press model is missing visual anchor '{name}'.");

    private static bool IsCrystalVariant(string name) =>
        string.Equals(name, "CrystalPile", StringComparison.Ordinal) ||
        string.Equals(name, "CrystalChunk_A", StringComparison.Ordinal) ||
        string.Equals(name, "CrystalChunk_B", StringComparison.Ordinal) ||
        string.Equals(name, "CrystalGranules", StringComparison.Ordinal);

    private static Vector3 QuadraticBezier(
        Vector3 start,
        Vector3 control,
        Vector3 end,
        float t)
    {
        float inverse = 1f - t;
        return inverse * inverse * start +
               2f * inverse * t * control +
               t * t * end;
    }

    private static float SafeDivide(float value, float divisor) =>
        Mathf.Abs(divisor) < 0.0001f ? value : Mathf.Abs(value / divisor);

    private static void HideNativeRenderers(GameObject root)
    {
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
            renderer.enabled = false;
    }

    private static void DisableReferenceAnimation(GameObject root)
    {
        foreach (Component component in root.GetComponentsInChildren<Component>(true))
        {
            if (component is Behaviour behaviour &&
                string.Equals(
                    component.GetType().Name,
                    "Animator",
                    StringComparison.Ordinal))
            {
                behaviour.enabled = false;
            }
        }
    }

    private static void DisableReferenceProcessVisuals(GameObject root)
    {
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            if (transform.name.StartsWith(
                    "FinishedTablet_",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "FreshTabletAssembly",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "FeedPowderAssembly",
                    StringComparison.Ordinal) ||
                string.Equals(
                    transform.name,
                    "DieFillAssembly",
                    StringComparison.Ordinal))
            {
                transform.gameObject.SetActive(false);
            }
        }
    }
}
