from ai.prediction_model import PricePredictor

def test_price_predictor():
    price_predictor = PricePredictor()

    # Replace with actual feature values or load from a sample
    sample_features = [1.0, 2.0, 3.0, 4.0, 5.0]

    try:
        predicted_price = price_predictor.predict_price(sample_features)
        print(f"Predicted price: {predicted_price}")
    except Exception as e:
        print("Prediction failed. Is the model trained and loaded?")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_price_predictor()