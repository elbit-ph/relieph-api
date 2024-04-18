import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split

from .dataset import biohazard, conflict, earthquake, fire, typhoon, volcanic
from joblib import dump

biohazard['label'] = 'biohazard'
conflict['label'] = 'conflict'
earthquake['label'] = 'earthquake'
fire['label'] = 'fire'
typhoon['label'] = 'typhoon'
volcanic['label'] = 'volcanic'

data = pd.concat([biohazard, conflict, earthquake, fire, typhoon, volcanic], ignore_index=True)

data = data.sample(frac=1).reset_index(drop=True)

X = data['headline']
y = data['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = make_pipeline(CountVectorizer(), MultinomialNB())

model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print("Model Accuracy:", accuracy)

dump(model, 'disaster_classifier.joblib')
