
import os
import re
import nltk

current_dir = os.path.dirname(__file__)
nltk.data.path.append(os.path.join(current_dir, '/nltk_data'))

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from .dataset import biohazard, conflict, earthquake, fire, typhoon, volcanic

lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    text = text.lower()

    tokens = nltk.word_tokenize(text)
    
    stop_words = set(stopwords.words('english'))

    filtered_tokens = [word for word in tokens if word not in stop_words]
    
    lemmatized_tokens = [lemmatizer.lemmatize(word) for word in filtered_tokens]
    
    preprocessed_text = ' '.join(lemmatized_tokens)
    return preprocessed_text

def preprocess_csv_files():
    
    datas = [biohazard, conflict, earthquake, fire, typhoon, volcanic]
    for data in datas:

        data['headline'] = data['headline'].apply(preprocess_text)
        data.to_csv(f'{data}', index=False)

