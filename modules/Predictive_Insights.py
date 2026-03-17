import pandas as pd
from typing import Dict, Any

from fastai.tabular.all import TabularDataLoaders, tabular_learner, Categorify, FillMissing, Normalize, mse

class StartupSuccessPredictor:
    """
    Experimental FastAI Module to predict composite scores or success labels 
    based on historical suitability assessment data.
    """
    
    def __init__(self):
        self.learner = None

    def train_dummy_model(self) -> str:
        """
        Trains a quick demonstration model using FastAI Tabular Learner on dummy data.
        In production, this would connect to a database of historical FFP Smart MVPs.
        """
        data = {
            'market_type': ['B2B SaaS', 'Consumer', 'Fintech', 'B2B SaaS', 'Healthcare', 'Marketplace'],
            'has_patents': [True, False, False, True, True, False],
            'revenue': [10000, 0, 50000, 2000, 150000, 0],
            'team_size': [3, 2, 5, 2, 8, 1],
            'composite_score': [85.5, 45.0, 72.1, 88.0, 92.5, 30.5]
        }
        df = pd.DataFrame(data)
        
        cat_names = ['market_type', 'has_patents']
        cont_names = ['revenue', 'team_size']
        procs = [Categorify, FillMissing, Normalize]
        
        try:
            # Create DataLoader
            dls = TabularDataLoaders.from_df(
                df, 
                path='.', 
                y_names='composite_score', 
                cat_names=cat_names, 
                cont_names=cont_names, 
                procs=procs, 
                bs=2
            )
            
            # Initialize Tabular Learner for Regression
            self.learner = tabular_learner(dls, metrics=mse)
            
            # Fast inference training cycle
            self.learner.fit_one_cycle(1)
            return "FastAI Tabular Model trained successfully on historical dummy data."
        except Exception as e:
            return f"Error training FastAI model: {str(e)}"

    def predict(self, startup_features: Dict[str, Any]) -> float:
        """
        Use the trained FastAI model to predict the startup's potential composite score.
        """
        if not self.learner:
            return 0.0
            
        df = pd.DataFrame([startup_features])
        row, clas, probs = self.learner.predict(df.iloc[0])
        return float(probs[0])

if __name__ == "__main__":
    # Test the FastAI Predictor natively
    predictor = StartupSuccessPredictor()
    result = predictor.train_dummy_model()
    print(result)
