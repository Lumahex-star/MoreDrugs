using MelonLoader;
using MoreDrugs.Content;
using MoreDrugs.Content.Mdma;
using S1API.Lifecycle;
using S1API.Products;

[assembly: MelonInfo(typeof(MoreDrugs.Core), MoreDrugs.ModInfo.Name, MoreDrugs.ModInfo.Version, MoreDrugs.ModInfo.Author)]
[assembly: MelonGame(MoreDrugs.ModInfo.GameDeveloper, MoreDrugs.ModInfo.GameName)]

namespace MoreDrugs;

public sealed class Core : MelonMod
{
    private DrugCatalog? _catalog;

    public override void OnInitializeMelon()
    {
        _catalog = new DrugCatalog(LoggerInstance, new IDrugContentModule[]
        {
            new MdmaModule(LoggerInstance),
        });

        CustomProductSaveProviderRegistry.Register(_catalog);
        GameLifecycle.OnPreLoad += OnPreLoad;
        GameLifecycle.OnLoadComplete += OnLoadComplete;
        LoggerInstance.Msg($"{ModInfo.Name} {ModInfo.Version} initialized.");
    }

    public override void OnApplicationQuit()
    {
        GameLifecycle.OnPreLoad -= OnPreLoad;
        GameLifecycle.OnLoadComplete -= OnLoadComplete;
        _catalog?.Dispose();
        _catalog = null;
    }

    private void OnPreLoad()
    {
        _catalog?.RegisterContent();
    }

    private void OnLoadComplete()
    {
        _catalog?.CompleteLoad();
    }
}

