import re
import os
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
from underthesea import word_tokenize

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

model = joblib.load(os.path.join(MODELS_DIR, 'best_sentiment_model.pkl'))
tfidf = joblib.load(os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl'))
le = joblib.load(os.path.join(MODELS_DIR, 'label_encoder.pkl'))


def preprocess(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[^a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ0-9\s]', ' ', text)
    tokens = word_tokenize(text)
    text = "_".join(tokens)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('_', ' ')
    return text


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing "text" field'}), 400

    raw_text = data['text']
    cleaned = preprocess(raw_text)
    vector = tfidf.transform([cleaned])
    pred_idx = model.predict(vector)[0]
    label = le.inverse_transform([pred_idx])[0]

    proba = model.decision_function(vector)[0]
    scores = {}
    for i, cls in enumerate(le.classes_):
        scores[cls] = round(float(proba[i]), 4)

    return jsonify({
        'text': raw_text,
        'sentiment': label,
        'scores': scores
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
