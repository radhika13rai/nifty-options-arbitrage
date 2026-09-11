"""Global Macro & News Intelligence Package Exports."""
from global_macro.indicators import MacroIndicatorSnapshot, GlobalMacroEngine, macro_engine
from global_macro.news_embedder import NewsItem, NewsEmbedding, FinancialNewsEmbedder, news_embedder
from global_macro.multimodal_fusion import MultimodalFusionResult, MultimodalFusionEngine, multimodal_fusion
from global_macro.news_feed import GlobalNewsFeed, news_feed
from global_macro.dataset import MacroHistoricalSample, GlobalMacroDatasetRepository, macro_dataset
from global_macro.trainer import TrainingResult, MultimodalWeightTrainer, macro_trainer
from global_macro.poller import LiveMacroPoller, live_macro_poller, categorize_headline

__all__ = [
    "MacroIndicatorSnapshot",
    "GlobalMacroEngine",
    "macro_engine",
    "NewsItem",
    "NewsEmbedding",
    "FinancialNewsEmbedder",
    "news_embedder",
    "MultimodalFusionResult",
    "MultimodalFusionEngine",
    "multimodal_fusion",
    "GlobalNewsFeed",
    "news_feed",
    "MacroHistoricalSample",
    "GlobalMacroDatasetRepository",
    "macro_dataset",
    "TrainingResult",
    "MultimodalWeightTrainer",
    "macro_trainer",
    "LiveMacroPoller",
    "live_macro_poller",
    "categorize_headline",
]
