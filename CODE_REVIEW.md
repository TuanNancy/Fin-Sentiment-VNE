# FinSentiment - Backend & Machine Learning Code Review

## 1. Tong quan he thong

**FinSentiment** la he thong phan tich cam xuc (sentiment analysis) cho van ban tai chinh tieng Viet, ho tro 3 nhan: **Tich cuc (positive)**, **Tieu cuc (negative)**, **Trung lap (neutral)**.

### Kien truc Microservice

```
Browser (Web UI)
    |
    v
+---------------------------+      +---------------------------+
| Backend (Express.js)      | ---> | ML Service (Flask)        |
| Port 3000                 | <--- | Port 5000                 |
| - API Gateway             |      | - Text Preprocessing      |
| - Static file server      |      | - TF-IDF Vectorization    |
| - Proxy to ML Service     |      | - Model Inference         |
+---------------------------+      +---------------------------+
    |                                       |
    v                                       v
public/index.html                   models/
                                    +-- best_sentiment_model.pkl
                                    +-- tfidf_vectorizer.pkl
                                    +-- label_encoder.pkl
```

### Cau truc thu muc

```
FinSentiment/
+-- backend/
|   +-- public/
|   |   +-- index.html          # Giao dien web
|   +-- server.js               # Express server + API proxy
|   +-- package.json            # Dependencies
+-- ml_service/
|   +-- app.py                  # Flask ML service
|   +-- requirements.txt        # Python dependencies
+-- models/
|   +-- best_sentiment_model.pkl    # Logistic Regression model
|   +-- tfidf_vectorizer.pkl        # TF-IDF vectorizer
|   +-- label_encoder.pkl           # Label encoder
+-- demo.ipynb                  # Notebook training & evaluation
+-- README.md
```

---

## 2. Backend - Express.js API Gateway

### 2.1. Cong nghe

| Thanh phan | Phien ban | Vai tro |
|------------|-----------|---------|
| Node.js | >= 18 | Runtime |
| Express.js | ^4.21.0 | Web framework |
| http-proxy-middleware | ^3.0.0 | Proxy middleware (duoc cai nhung khong dung) |

### 2.2. Phan tich `server.js` (27 dong)

#### Luong hoat dong

```
Browser --> POST /api/predict { text: "..." }
    |
    v
Express Middleware:
    +-- express.json()            --> Parse JSON body
    +-- express.static(public/)   --> Serve file tinh (index.html)
    |
    v
Route Handler: POST /api/predict
    |
    +-- 1. Nhan request tu browser
    +-- 2. Forward sang ML Service: POST http://localhost:5000/predict
    |      (dung native fetch() cua Node 18+)
    +-- 3. Nhan response JSON tu ML Service
    +-- 4. Tra ve cho browser (proxy passthrough)
    |
    +-- Error --> 502 "ML service unavailable"
    v
Browser nhan ket qua
```

#### Code walkthrough

```javascript
// server.js - 27 dong, thiet ke toi gian
const express = require('express');
const path = require('path');

const app = express();
const PORT = 3000;
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000';

// Middleware
app.use(express.json());                                  // Parse JSON body
app.use(express.static(path.join(__dirname, 'public')));  // Serve static files

// API Proxy - chuyen tiep request sang ML Service
app.post('/api/predict', async (req, res) => {
  try {
    const response = await fetch(`${ML_SERVICE_URL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    res.status(502).json({ error: 'ML service unavailable' });
  }
});

app.listen(PORT, () => {
  console.log(`Backend running at http://localhost:${PORT}`);
});
```

#### Nhan xet

| Uu diem | Nhuoc diem |
|---------|------------|
| Code ngan gon, de hieu | Khong co input validation o backend |
| Dung native `fetch()` (Node 18+) | Khong co retry mechanism |
| Environment variable cho ML URL | Khong co rate limiting |
| Error handling co ban (502) | Khong co logging |
| Serve static frontend | Khong co CORS config (khong can vi cung origin) |

**Luu y:** `http-proxy-middleware` duoc khai bao trong `package.json` nhung **khong duoc su dung** trong `server.js`. Backend tu viet proxy bang `fetch()` thay vi dung middleware.

---

## 3. Frontend - Single Page Application

### 3.1. Phan tich `index.html` (204 dong)

#### Luong hoat dong

```
User nhap text --> Nhan "Phan tich" (hoac Ctrl+Enter)
    |
    v
JavaScript: analyze()
    +-- 1. Lay text tu textarea
    +-- 2. Disable button, hien "Dang phan tich..."
    +-- 3. POST /api/predict { text: "..." }
    +-- 4. Nhan response: { sentiment, scores }
    +-- 5. Hien thi:
    |      +-- Sentiment label (mau sac: xanh=positive, do=negative, xam=neutral)
    |      +-- Score bars (ty le phan tram tuong doi so voi max score)
    +-- 6. Error handling: hien error box neu co loi
```

#### Logic hien thi score bars

```javascript
// Score bars duoc render tuong doi so voi max score
const maxScore = Math.max(...Object.values(scores));
for (const [cls, val] of Object.entries(scores)) {
  const pct = Math.max(0, val / maxScore) * 100;  // Normalize relative to max
  // Render bar with width = pct%
}
```

**Luu y:** Score bars hien thi ty le tuong doi (relative), khong phai gia tri tuyet doi. Neu model tra ve `decision_function` values (co the am), logic nay van hoat dong nhung co the gay hieu nham.

---

## 4. ML Service - Flask Inference Server

### 4.1. Cong nghe

| Thu vien | Phien ban | Vai tro |
|----------|-----------|---------|
| Flask | 3.1.1 | Web framework |
| flask-cors | 5.0.1 | CORS support |
| scikit-learn | 1.6.1 | ML model + TF-IDF |
| underthesea | 9.5.0 | Vietnamese NLP (word segmentation) |
| joblib | 1.5.3 | Model serialization |

### 4.2. Phan tich `app.py` (63 dong)

#### Luong hoat dong khi khoi dong

```
Server start
    |
    v
Load 3 artifacts tu models/:
    +-- best_sentiment_model.pkl  --> Logistic Regression model
    +-- tfidf_vectorizer.pkl      --> TF-IDF vectorizer (da fit)
    +-- label_encoder.pkl         --> Label encoder (da fit)
    |
    v
Flask app ready tren port 5000
```

#### Luong xu ly request `/predict`

```
POST /predict { "text": "Gia co phieu tang manh" }
    |
    v
1. Input validation
    +-- Kiem tra field "text" ton tai
    +-- Missing --> 400 { "error": "Missing \"text\" field" }
    |
    v
2. Preprocessing (preprocess function)
    +-- a. Lowercase: "gia co phieu tang manh"
    +-- b. Remove URLs/emails: (regex)
    +-- c. Remove special chars: chi giu chu cai tieng Viet + so
    +-- d. Word segmentation: underthesea.word_tokenize()
    |      --> ["gia", "co phieu", "tang", "manh"]
    +-- e. Join bang "_": "gia_co_phieu_tang_manh"
    +-- f. Normalize whitespace
    +-- g. Replace "_" --> " ": "gia co phieu tang manh"
    |
    v
3. Vectorization
    +-- tfidf.transform([cleaned_text])
        --> Sparse matrix (1, 11595)
    |
    v
4. Prediction
    +-- model.predict(vector) --> [label_index]
    +-- le.inverse_transform([label_index]) --> "positive"
    |
    v
5. Confidence scores
    +-- model.decision_function(vector) --> [score_neg, score_neu, score_pos]
    +-- Round 4 chu so thap phan
    |
    v
6. Response
    {
      "text": "Gia co phieu tang manh",
      "sentiment": "positive",
      "scores": { "negative": 0.05, "neutral": 0.12, "positive": 0.83 }
    }
```

#### Code walkthrough

```python
# app.py - 63 dong

# Load models (chay 1 lan khi server khoi dong)
model = joblib.load('models/best_sentiment_model.pkl')
tfidf = joblib.load('models/tfidf_vectorizer.pkl')
le = joblib.load('models/label_encoder.pkl')

# Preprocessing pipeline
def preprocess(text):
    text = text.lower()                                          # Lowercase
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)         # Remove URLs
    text = re.sub(r'\S+@\S+', '', text)                          # Remove emails
    text = re.sub(r'[^a-z a a a a a...d0-9\s]', ' ', text)      # Remove special chars
    tokens = word_tokenize(text)                                  # Vietnamese segmentation
    text = "_".join(tokens)                                       # Join tokens
    text = re.sub(r'\s+', ' ', text).strip()                     # Normalize whitespace
    text = text.replace('_', ' ')                                 # Replace underscores
    return text

# Predict endpoint
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing "text" field'}), 400

    raw_text = data['text']
    cleaned = preprocess(raw_text)
    vector = tfidf.transform([cleaned])                           # Vectorize
    pred_idx = model.predict(vector)[0]                           # Predict
    label = le.inverse_transform([pred_idx])[0]                   # Decode label

    proba = model.decision_function(vector)[0]                    # Confidence scores
    scores = {}
    for i, cls in enumerate(le.classes_):
        scores[cls] = round(float(proba[i]), 4)

    return jsonify({
        'text': raw_text,
        'sentiment': label,
        'scores': scores
    })
```

#### Nhan xet

| Uu diem | Nhuoc diem |
|---------|------------|
| Preprocessing pipeline ro rang | Khong co caching cho repeated requests |
| Load model 1 lan (efficient) | Khong co batch prediction |
| Error handling co ban | Khong co logging |
| CORS enabled | `decision_function` tra ve raw scores, khong phai probabilities |

---

## 5. Machine Learning - Chi tiet thuat toan

### 5.1. Dataset

| Thuoc tinh | Gia tri |
|------------|---------|
| Nguon | VLSP 2016 Sentiment Analysis (HuggingFace: `ura-hcmut/vlsp2016`) |
| Tap train | 5,100 mau |
| Tap test | 1,050 mau |
| So lop | 3 (negative, neutral, positive) |
| Phan bo | **Can bang hoan hao**: 1,700 mau/lop |
| Do dai trung binh | ~130 ky tu/mau |
| Ngon ngu | Tieng Viet |

### 5.2. Tien xu ly van ban (Text Preprocessing)

#### Pipeline chi tiet

```
Raw Text: "Gia co phieu VIC tang 5% hom nay! https://example.com"
    |
    v
Step 1: Lowercase
    --> "gia co phieu vic tang 5% hom nay! https://example.com"
    |
    v
Step 2: Remove URLs (regex: http\S+|www\S+|https\S+)
    --> "gia co phieu vic tang 5% hom nay! "
    |
    v
Step 3: Remove emails (regex: \S+@\S+)
    --> (khong thay doi neu khong co email)
    |
    v
Step 4: Remove special characters
    Regex: [^a-z a a a a a...d0-9\s]
    --> "gia co phieu vic tang 5  hom nay  "
    (giu chu cai tieng Viet co dau + so + whitespace)
    |
    v
Step 5: Vietnamese word segmentation (underthesea.word_tokenize)
    --> ["gia", "co phieu", "vic", "tang", "5", "hom nay"]
    |
    v
Step 6: Join tokens bang "_"
    --> "gia_co_phieu_vic_tang_5_hom_nay"
    |
    v
Step 7: Normalize whitespace
    --> "gia_co_phieu_vic_tang_5_hom_nay"
    |
    v
Step 8: Replace "_" --> " " (de TF-IDF tu bat n-gram)
    --> "gia co phieu vic tang 5 hom nay"
    |
    v
Final: "gia co phieu vic tang 5 hom nay"
```

#### Tai sao can word segmentation?

Tieng Viet la ngon ngu **don am tiet** (isolating language), moi tu co the gom nhieu am tiet viet cach nhau. Vi du:
- "co phieu" = 1 tu (stock), gom 2 am tiet
- "tang manh" = 2 tu, gom 4 am tiet

Neu khong segment, TF-IDF se coi "co" va "phieu" la 2 tu rieng biet --> mat ngu nghia.

`underthesea.word_tokenize` su dung mo hinh **CRF (Conditional Random Field)** hoac **deep learning** de nhan dien boundaries giua cac tu.

### 5.3. Trich xuat dac trung - TF-IDF

#### Khai niem

**TF-IDF** (Term Frequency - Inverse Document Frequency) la phuong phap chuyen doi van ban thanh vector so dua tren tan suat xuat hien cua tu, co trong so theo do hiem.

#### Cong thuc

```
TF-IDF(t, d) = TF(t, d) x IDF(t)

Trong do:
- TF(t, d) = Term Frequency: so lan tu t xuat hien trong van ban d
- IDF(t) = Inverse Document Frequency: log(N / df(t))
  - N = tong so van ban trong corpus
  - df(t) = so van ban chua tu t (document frequency)
```

#### Cau hinh trong project

```python
TfidfVectorizer(
    max_features=15000,      # Gioi han 15,000 features (tu/cum tu) pho bien nhat
    ngram_range=(1, 2),      # Unigram (1 tu) + Bigram (2 tu lien tiep)
    min_df=3,                # Loai bo tu xuat hien < 3 lan (qua hiem)
    max_df=0.9,              # Loai bo tu xuat hien trong > 90% van ban (qua pho bien)
    sublinear_tf=True        # Log scaling: TF = 1 + log(TF)
)
```

#### Giai thich tham so

| Tham so | Gia tri | Y nghia |
|---------|---------|---------|
| `max_features` | 15,000 | Gioi han so chieu vector, tranh curse of dimensionality |
| `ngram_range` | (1, 2) | Bat ca unigram ("tot") va bigram ("rat tot") |
| `min_df` | 3 | Loai bo tu qua hiem (noise, typo) |
| `max_df` | 0.9 | Loai bo tu qua pho bien (co the la stopword) |
| `sublinear_tf` | True | Giam anh huong cua tu lap lai nhieu (log scaling) |

#### Sublinear TF scaling

```
Normal TF:      TF(t, d) = count(t in d)
Sublinear TF:   TF(t, d) = 1 + log(count(t in d))  neu count > 0
                            = 0                     neu count = 0

Vi du: tu "tang" xuat hien 10 lan trong van ban
- Normal TF: 10
- Sublinear TF: 1 + log(10) ~ 3.32
```

#### Ket qua

- Ma tran train: **(5100, 11595)** - 5,100 van ban, 11,595 features
- Ma tran test: **(1050, 11595)** - 1,050 van ban, 11,595 features (cung vocabulary)

### 5.4. Ma hoa nhan - Label Encoding

```python
LabelEncoder()
- "negative" --> 0
- "neutral"  --> 1
- "positive" --> 2
```

### 5.5. Cac thuat toan phan loai duoc danh gia

#### 5.5.1. Linear SVM (Support Vector Machine)

**Nguyen ly:**
```
Tim sieu phang (hyperplane) toi uu phan tach cac lop trong khong gian nhieu chieu.

Ham muc tieu:
  min 1/2 ||w||^2 + C * sum(xi_i)
  subject to: y_i * (w . x_i + b) >= 1 - xi_i, xi_i >= 0

Trong do:
- w: vector trong so
- b: bias
- C: regularization parameter (mac dinh C=1.0)
- xi_i: slack variables (cho phep phan loai sai)
```

**Cau hinh:**
```python
LinearSVC(max_iter=2000, random_state=42)
```

**Ket qua:**
```
Accuracy: 0.6981
Weighted F1: 0.6988

              precision  recall  f1-score   support
    negative      0.69    0.71    0.70       350
     neutral      0.65    0.67    0.66       350
    positive      0.77    0.72    0.74       350
```

#### 5.5.2. Logistic Regression (Duoc chon)

**Nguyen ly:**
```
Mo hinh tuyen tinh cho bai toan phan loai da lop (multinomial).

Ham softmax (cho 3 lop):
  P(y=k|x) = exp(w_k . x + b_k) / sum_j exp(w_j . x + b_j)

Ham mat mat (cross-entropy):
  L = -sum_i sum_k y_ik * log(P(y=k|x_i)) + 1/2 ||w||^2

Trong do:
- w_k: vector trong so cho lop k
- b_k: bias cho lop k
- y_ik: 1 neu mau i thuoc lop k, 0 neu nguoc lai
```

**Cau hinh:**
```python
LogisticRegression(max_iter=1000, random_state=42)
```

**Ket qua:**
```
Accuracy: 0.7048
Weighted F1: 0.7057  <-- CAO NHAT

              precision  recall  f1-score   support
    negative      0.69    0.69    0.69       350
     neutral      0.66    0.70    0.68       350
    positive      0.78    0.72    0.75       350
```

**Tai sao duoc chon:**
- Weighted F1 cao nhat (0.7057 > 0.6988 > 0.6880)
- Cung cap `decision_function()` cho confidence scores
- Mo hinh don gian, de deploy, inference nhanh
- Interpretable (co the xem feature weights)

#### 5.5.3. Multinomial Naive Bayes

**Nguyen ly:**
```
Ap dung dinh ly Bayes voi gia dinh "naive" (doc lap co dieu kien):

P(class|x) ~ P(class) * product P(x_i|class)

Voi phan phoi Multinomial:
  P(x_i|class) = (count(x_i, class) + alpha) / (sum count(x_j, class) + alpha * V)

Trong do:
- alpha: Laplace smoothing (mac dinh alpha=1.0)
- V: kich thuoc vocabulary
```

**Cau hinh:**
```python
MultinomialNB()  # Default parameters
```

**Ket qua:**
```
Accuracy: 0.6867
Weighted F1: 0.6880

              precision  recall  f1-score   support
    negative      0.68    0.68    0.68       350
     neutral      0.62    0.70    0.66       350
    positive      0.77    0.68    0.73       350
```

### 5.6. So sanh tong hop

| Mo hinh | Accuracy | Weighted F1 | Precision (pos) | Recall (neu) |
|---------|----------|-------------|-----------------|--------------|
| Linear SVM | 0.6981 | 0.6988 | 0.77 | 0.67 |
| **Logistic Regression** | **0.7048** | **0.7057** | **0.78** | **0.70** |
| Multinomial NB | 0.6867 | 0.6880 | 0.77 | 0.70 |

### 5.7. Tieu chi chon mo hinh

```python
# Trong demo.ipynb, mo hinh duoc chon dua tren Weighted F1-score
if f1 > best_f1:
    best_f1 = f1
    best_model_name = name
    best_model_obj = model
```

**Tai sao dung Weighted F1 thay vi Accuracy?**
- F1-score can bang giua Precision va Recall
- Weighted F1 tinh trung binh co trong so theo support (so mau moi lop)
- Phu hop hon cho bai toan da lop voi phan bo lop can bang

---

## 6. Flow hoat dong End-to-End

### 6.1. Training Flow (demo.ipynb)

```
+------------------------------------------------------------------+
|                    TRAINING PIPELINE                               |
+------------------------------------------------------------------+
|                                                                    |
|  1. LOAD DATA                                                      |
|     +-- HuggingFace: ura-hcmut/vlsp2016                           |
|     +-- df_train: 5,100 mau                                       |
|     +-- df_test: 1,050 mau                                        |
|                                                                    |
|  2. EDA (Exploratory Data Analysis)                                |
|     +-- Kiem tra null values --> 0 null                           |
|     +-- Kiem tra class balance --> 1700/1700/1700 (can bang)      |
|     +-- Phan tich do dai van ban --> mean=130 chars               |
|                                                                    |
|  3. PREPROCESSING                                                  |
|     +-- Lowercase                                                  |
|     +-- Remove URL/email/special chars                             |
|     +-- Vietnamese word segmentation (underthesea)                 |
|     +-- Join tokens bang "_" --> replace "_" --> " "              |
|                                                                    |
|  4. LABEL ENCODING                                                 |
|     LabelEncoder: negative=0, neutral=1, positive=2                |
|                                                                    |
|  5. TF-IDF VECTORIZATION                                           |
|     TfidfVectorizer(max_features=15000, ngram=(1,2), ...)          |
|     --> Sparse matrix (5100, 11595)                                |
|                                                                    |
|  6. MODEL TRAINING & EVALUATION                                    |
|     +-- LinearSVC     --> F1: 0.6988                               |
|     +-- LogisticRegression --> F1: 0.7057 <-- BEST                |
|     +-- MultinomialNB --> F1: 0.6880                               |
|                                                                    |
|  7. SAVE ARTIFACTS                                                 |
|     +-- best_sentiment_model.pkl  (Logistic Regression)            |
|     +-- tfidf_vectorizer.pkl      (fitted TF-IDF)                  |
|     +-- label_encoder.pkl         (fitted LabelEncoder)            |
|                                                                    |
+------------------------------------------------------------------+
```

### 6.2. Inference Flow (Production)

```
+------------------------------------------------------------------+
|                    INFERENCE PIPELINE                               |
+------------------------------------------------------------------+
|                                                                    |
|  User --> Browser --> POST /api/predict { text: "..." }            |
|                    |                                               |
|                    v                                               |
|  +-- Backend (Express:3000) --------------------------------+     |
|  |  1. Parse JSON body                                      |     |
|  |  2. Forward --> POST http://localhost:5000/predict       |     |
|  |  3. Return response to browser                           |     |
|  +----------------------------------------------------------+     |
|                    |                                               |
|                    v                                               |
|  +-- ML Service (Flask:5000) --------------------------------+    |
|  |                                                            |    |
|  |  STARTUP (1 lan):                                          |    |
|  |  +-- Load model.pkl   --> Logistic Regression              |    |
|  |  +-- Load vectorizer.pkl --> TF-IDF (fitted)               |    |
|  |  +-- Load encoder.pkl --> LabelEncoder (fitted)            |    |
|  |                                                            |    |
|  |  PER REQUEST:                                              |    |
|  |  1. Validate input (field "text" exists)                   |    |
|  |  2. Preprocess text:                                       |    |
|  |     +-- lowercase --> remove URL/email --> clean chars     |    |
|  |     +-- word_tokenize (underthesea)                        |    |
|  |     +-- normalize whitespace                               |    |
|  |  3. Vectorize: tfidf.transform([cleaned_text])             |    |
|  |     --> Sparse vector (1, 11595)                           |    |
|  |  4. Predict: model.predict(vector)                         |    |
|  |     --> Label index (0/1/2)                                |    |
|  |  5. Decode: le.inverse_transform([idx])                    |    |
|  |     --> "positive" / "negative" / "neutral"                |    |
|  |  6. Scores: model.decision_function(vector)                |    |
|  |     --> [score_neg, score_neu, score_pos] (raw margins)    |    |
|  |  7. Return JSON response                                   |    |
|  |                                                            |    |
|  +------------------------------------------------------------+   |
|                    |                                               |
|                    v                                               |
|  Browser renders:                                                  |
|  +-- Sentiment label (color-coded)                                 |
|  +-- Score bars (relative to max score)                            |
|                                                                    |
+------------------------------------------------------------------+
```

---

## 7. Cac file artifacts (.pkl)

| File | Noi dung | Kich thuoc |
|------|----------|------------|
| `best_sentiment_model.pkl` | Logistic Regression model (weights + bias) | ~1-2 MB |
| `tfidf_vectorizer.pkl` | TF-IDF vectorizer (vocabulary 11,595 terms) | ~1-2 MB |
| `label_encoder.pkl` | Label encoder (3 classes) | ~1 KB |

**Dependency chain:**
```
Text Input
    |
    +-- tfidf_vectorizer.pkl --> transform --> Sparse vector (1, 11595)
    |
    +-- best_sentiment_model.pkl --> predict --> Label index (0/1/2)
    |
    +-- label_encoder.pkl --> inverse_transform --> "positive"/"negative"/"neutral"
```

---

## 8. Danh gia tong the

### 8.1. Diem manh

1. **Kien truc microservice ro rang** - Tach biet API gateway va ML inference
2. **Preprocessing pipeline nhat quan** - Cung logic giua training va inference
3. **Model selection co phuong phap** - So sanh 3 mo hinh, chon dua tren Weighted F1
4. **TF-IDF cau hinh hop ly** - sublinear_tf, ngram_range, min/max_df
5. **Dataset can bang** - Khong can xu ly class imbalance
6. **Code sach, de doc** - Ca backend va ML service deu ngan gon

### 8.2. Diem can cai thien

1. **`decision_function()` khong phai probability** - Scores tra ve la margin distances, khong phai xac suat. Frontend hien thi duoi dang percentage co the gay hieu nham.
2. **Accuracy ~70%** - Con kha thap, co the cai thien bang:
   - Deep learning (PhoBERT, viBERT)
   - Word embeddings (Word2Vec, FastText)
   - Tang du lieu training
3. **Khong co validation o backend gateway** - Input validation chi o ML Service
4. **Khong co timeout/retry** cho request toi ML Service
5. **`http-proxy-middleware` khong duoc su dung** du da cai trong dependencies
6. **Khong co logging/monitoring** cho ca 2 service
7. **Khong co caching** cho cac request trung lap
8. **Khong co authentication/authorization** cho API

### 8.3. Goi y nang cap

| Hang muc | Hien tai | De xuat |
|----------|----------|---------|
| Model | Logistic Regression | PhoBERT / viBERT (transformer-based) |
| Tokenizer | underthesea word_tokenize | PhoTokenizer (BPE) |
| Features | TF-IDF (sparse) | Contextual embeddings (dense) |
| Accuracy | ~70% | 85-90%+ voi transformers |
| API Security | Khong co | API key / JWT |
| Monitoring | Khong co | Prometheus + Grafana |
| Caching | Khong co | Redis cache cho predictions |
| Batch predict | Khong ho tro | Them endpoint `/predict/batch` |

---

## 9. Ket luan

FinSentiment la mot project **well-structured** voi kien truc microservice ro rang, pipeline ML nhat quan, va code sach. He thong hoat dong end-to-end tu text input --> preprocessing --> vectorization --> prediction --> response.

**Thuat toan ML chinh:**
- **TF-IDF** (Term Frequency - Inverse Document Frequency) voi sublinear TF scaling, unigram + bigram
- **Logistic Regression** (multinomial) - duoc chon sau khi so sanh voi Linear SVM va Multinomial Naive Bayes
- **Vietnamese word segmentation** bang `underthesea` (CRF/deep learning-based)

**Ket qua:**
- Accuracy: 70.48%
- Weighted F1: 70.57%
- Best class: positive (F1: 0.75)
- Weakest class: neutral (F1: 0.68)

**Huong phat trien:**
- Nang cap len transformer-based models (PhoBERT) de dat 85-90%+
- Them monitoring, logging, authentication
- Ho tro batch prediction va caching
