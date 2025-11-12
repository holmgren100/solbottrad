from ai.sentiment_model import SentimentAnalyzer

def test_sentiment_analyzer():
    sentiment_analyzer = SentimentAnalyzer()
    sentiment_analyzer.is_trained = True  # Mark as trained for testing

    # Test positive sentiment
    positive_text = "This project is amazing and has great potential!"
    try:
        positive_score = sentiment_analyzer.predict_sentiment(positive_text)
        print(f"Positive sentiment: {positive_score}")
    except Exception as e:
        print("Prediction failed for positive sentiment.")
        print(f"Error: {e}")

    # Test negative sentiment
    negative_text = "This project is terrible and will fail."
    try:
        negative_score = sentiment_analyzer.predict_sentiment(negative_text)
        print(f"Negative sentiment: {negative_score}")
    except Exception as e:
        print("Prediction failed for negative sentiment.")
        print(f"Error: {e}")

    # Test neutral sentiment
    neutral_text = "This is a project."
    try:
        neutral_score = sentiment_analyzer.predict_sentiment(neutral_text)
        print(f"Neutral sentiment: {neutral_score}")
    except Exception as e:
        print("Prediction failed for neutral sentiment.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sentiment_analyzer()