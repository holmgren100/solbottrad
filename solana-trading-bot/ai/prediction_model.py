import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from utils.logger import setup_logger
from exceptions.custom_exceptions import ModelNotTrainedError

class PricePredictor:
    def __init__(self):
        """Initialize the PricePredictor with a scaler, model, and logger."""
        self.logger = setup_logger(__name__)  # Move logger initialization to top
        self.logger.info("Initializing PricePredictor")

        try:
            self.scaler = StandardScaler()
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3
            )
            self.is_trained = False
            self.logger.info("PricePredictor initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing PricePredictor: {str(e)}")
            raise

    def prepare_features(self, data):
        """
        Prepare features for prediction.

        Args:
            data (dict): Dictionary containing feature values.

        Returns:
            np.ndarray: Prepared features array.

        Raises:
            KeyError: If required features are missing.
            Exception: For other preparation errors.
        """
        self.logger.debug(f"Preparing features from data: {data}")
        required_features = ['volume', 'social_score', 'wallet_activity',
                           'price_change_24h', 'market_cap']

        try:
            # Verify all required features are present
            missing_features = [f for f in required_features if f not in data]
            if missing_features:
                raise KeyError(f"Missing required features: {missing_features}")

            features = [data[feature] for feature in required_features]
            features_array = np.array(features).reshape(1, -1)
            self.logger.debug(f"Features prepared successfully: {features_array}")
            return features_array
        except KeyError as e:
            self.logger.error(f"Missing required feature: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error preparing features: {str(e)}")
            raise

    def train(self, features, prices):
        """
        Train the price prediction model.

        Args:
            features (np.ndarray): The input features for training.
            prices (np.ndarray): The target prices for training.

        Raises:
            ValueError: If features or prices are invalid.
            Exception: If an error occurs during training.
        """
        self.logger.info("Starting model training")
        try:
            # Input validation
            if features.shape[0] != prices.shape[0]:
                raise ValueError("Number of features and prices must match")

            if features.shape[1] != 5:  # Assuming 5 features as per prepare_features
                raise ValueError("Features must have 5 columns")

            scaled_features = self.scaler.fit_transform(features)
            self.model.fit(scaled_features, prices)
            self.is_trained = True
            self.logger.info(f"Model trained successfully with {features.shape[0]} samples")
        except Exception as e:
            self.logger.error(f"Error training price model: {str(e)}")
            raise

    def predict_price(self, features):
        """
        Predict the price using the trained model.

        Args:
            features (list, dict, or np.ndarray): Feature values for prediction.

        Returns:
            float: Predicted price.

        Raises:
            ModelNotTrainedError: If the model hasn't been trained.
            Exception: If an error occurs during prediction.
        """
        if not self.is_trained:
            self.logger.error("Attempted prediction with untrained model")
            raise ModelNotTrainedError("Price model needs training first")
        
        try:
            # Handle different input types
            if isinstance(features, dict):
                features = self.prepare_features(features)
            elif isinstance(features, list):
                features = np.array(features).reshape(1, -1)
            elif isinstance(features, np.ndarray):
                if features.ndim == 1:
                    features = features.reshape(1, -1)
            
            scaled_features = self.scaler.transform(features)
            prediction = self.model.predict(scaled_features)[0]
            
            self.logger.info(f"Predicted price: {prediction}")
            return float(prediction)
            
        except Exception as e:
            self.logger.error(f"Error in predict_price: {str(e)}")
            raise

    def predict_movement(self, current_data):
        """
        Predict price movement direction and magnitude.

        Args:
            current_data (dict): Dictionary containing current market data.

        Returns:
            dict: Prediction results including direction, change, and confidence.

        Raises:
            ModelNotTrainedError: If the model hasn't been trained.
            Exception: If an error occurs during prediction.
        """
        self.logger.debug(f"Predicting movement for data: {current_data}")

        if not self.is_trained:
            pythonself.logger.error("Attempted prediction with untrained model")