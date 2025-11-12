from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from config.settings import settings
from utils.logger import setup_logger
from api.twitter_api import TwitterAPI

# Custom exception for untrained model
class ModelNotTrainedError(Exception):
    """Exception raised when the sentiment model is not trained."""
    pass

class SentimentAnalyzer:
    def __init__(self):
        """
        Initialize the SentimentAnalyzer with a vectorizer, model, and logger.
        """
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.model = RandomForestClassifier()
        self.is_trained = False
        self.logger = setup_logger(__name__)  # Use setup_logger with module name
        self.twitter = TwitterAPI()

    def train(self, texts, labels):
        """
        Train the sentiment model with text data.

        Args:
            texts (list of str): The training text data.
            labels (list of int): The corresponding labels (1 for positive, 0 for negative).

        Raises:
            Exception: If an error occurs during training.
        """
        try:
            features = self.vectorizer.fit_transform(texts)
            self.model.fit(features, labels)
            self.is_trained = True
            self.logger.info("Sentiment model trained successfully")
        except Exception as e:
            self.logger.error(f"Error training sentiment model: {str(e)}")
            raise

    def predict_sentiment(self, text):
        """
        Predict the sentiment for a given text.

        Args:
            text (str): The input text to analyze.

        Returns:
            dict: A dictionary containing the sentiment, confidence, and score.

        Raises:
            ModelNotTrainedError: If the model has not been trained.
            Exception: If an error occurs during prediction.
        """
        if not self.is_trained:
            raise ModelNotTrainedError("Sentiment model needs training first")

        try:
            features = self.vectorizer.transform([text])
            prediction = self.model.predict(features)[0]
            confidence = self.model.predict_proba(features)[0].max()

            return {
                'sentiment': 'positive' if prediction == 1 else 'negative',
                'confidence': confidence,
                'score': float(confidence) if prediction == 1 else float(-confidence)
            }
        except Exception as e:
            self.logger.error(f"Error predicting sentiment: {str(e)}")
            raise