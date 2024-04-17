import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from joblib import dump

from .dataset import biohazard, conflict, earthquake, fire, typhoon, volcanic

biohazard['label'] = 'biohazard'
conflict['label'] = 'conflict'
earthquake['label'] = 'earthquake'
fire['label'] = 'fire'
typhoon['label'] = 'typhoon'
volcanic['label'] = 'volcanic'

# Concatenating datasets
data = pd.concat([biohazard, conflict, earthquake, fire, typhoon, volcanic], ignore_index=True)

# Shuffle the data
data = data.sample(frac=1).reset_index(drop=True)

# Splitting into features and target
X = data['headline']
y = data['label']

# Splitting data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Creating pipeline
model = make_pipeline(CountVectorizer(), MultinomialNB())

# Training the model
model.fit(X_train, y_train)

# Evaluating the model
accuracy = model.score(X_test, y_test)
print("Model Accuracy:", accuracy)

# Saving the model
dump(model, 'disaster_classifier.joblib')
