import os
import numpy as np
from joblib import load
from .preprocessing import preprocess_text

current_dir = os.path.dirname(__file__)

model_file_path = os.path.join(current_dir, 'model/disaster_classifier.joblib')

model = load(model_file_path)

def classify_headline(data):
    headline = data

    preprocessed_headline = preprocess_text(headline)

    prediction_probabilities = model.predict_proba([preprocessed_headline])[0]

    max_prob_index = np.argmax(prediction_probabilities)

    predicted_category = model.classes_[max_prob_index]

    prediction_score = prediction_probabilities[max_prob_index]
    
    min_prediction_score_threshold = 0.95
    
    if prediction_score >= min_prediction_score_threshold:
        return {"prediction": predicted_category}
    else:
        return {"prediction": "non-disaster"}