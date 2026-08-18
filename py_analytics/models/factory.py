import joblib
from pathlib import Path

from .base import Strategy
from .isolationforest_strategy import IsolationForestStrategy
from .river_strategy import RiverStrategy

def create_strategy(strategy_name: str, models_path: str) -> Strategy:
    """
    Initiates or loads an anomaly detection model, given the name and the folder path of the saved models.
    
    Args:
        strategy_name: str (Currently can be only [SKlearnIsolatedForest, RiverHalfSpaceTrees])
        models_path: str (Path to the folder with saved, already-existing models)

    Returns:
        strategy: Strategy (An anomaly detection model object)
    """
    if strategy_name == "RiverHalfSpaceTrees":
        strategy = RiverStrategy()
    elif strategy_name == "SKlearnIsolatedForest":
        strategy = IsolationForestStrategy()
    elif strategy_name == "None":
        strategy = None
    elif ".pkl" in strategy_name: # If a specific path to a model is given, load the given model.
        models = get_saved_models(folder_path=models_path)
        if strategy_name in [str(model) for model in models]:
            strategy = joblib.load(strategy_name)['model_state']
            strategy.logger.info(f"--- [LOADED] {joblib.load(strategy_name)['metadata']}")
        else:
            raise NameError("--- [ERROR] Please provide a valid path to load an Amodel model")
    else:
        raise NameError("--- [ERROR] Please provide a valid Amodel name")

    return strategy

def get_saved_models(folder_path: str, extension: str = "*.pkl", get_latest: bool = True):
    path = Path(folder_path)
    folder_models = list(path.glob("*"))
    if not folder_models:
        return ""
    
    saves = []
    print(folder_models)
    for folder_model in folder_models:
        saves.extend(list(folder_model.glob(extension)))

    return saves