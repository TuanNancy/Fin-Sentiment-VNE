# FinSentiment - Phân tích cảm xúc tài chính tiếng Việt

Hệ thống phân tích cảm xúc (sentiment analysis) cho văn bản tài chính tiếng Việt, hỗ trợ 3 nhãn: **Tích cực**, **Tiêu cực**, **Trung lập**.

Được xây dựng với kiến trúc microservice: backend Express.js làm API gateway + phục vụ giao diện web, và ML service Flask xử lý inference mô hình.

![FinSentiment](https://img.shields.io/badge/FinSentiment-NLP-blue) ![Python](https://img.shields.io/badge/Python-3.11+-green) ![Node.js](https://img.shields.io/badge/Node.js-18+-orange) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu](#yêu-cầu)
- [Cài đặt](#cài-đặt)
- [Cách chạy](#cách-chạy)
- [API Reference](#api-reference)
- [Pipeline xử lý](#pipeline-xử-lý)
- [Kết quả mô hình](#kết-quả-mô-hình)
- [Dataset](#dataset)
- [Demo](#demo)
- [Đóng góp](#đóng-góp)
- [License](#license)

---

## Tổng quan

FinSentiment là project NLP tập trung vào bài toán phân loại cảm xúc cho văn bản tiếng Việt trong lĩnh vực tài chính. Hệ thống bao gồm:

- **ML Pipeline**: Tiền xử lý văn bản tiếng Việt (tokenization bằng `underthesea`), trích xuất đặc trưng TF-IDF, và phân loại bằng Logistic Regression.
- **ML Service**: Flask API phục vụ inference, trả về nhãn cảm xúc và điểm confidence.
- **Backend**: Express.js làm API gateway, proxy request đến ML service và phục vụ frontend.
- **Frontend**: Giao diện web đơn giản cho phép nhập văn bản và xem kết quả phân tích trực quan.

## Kiến trúc hệ thống

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Browser    │─────>│  Backend (Express)│─────>│  ML Service      │
│   (Web UI)   │<─────│  Port 3000       │<─────│  (Flask)         │
│              │      │                  │      │  Port 5000       │
└─────────────┘      └──────────────────┘      └──────────────────┘
                              │                         │
                              │                         ├── best_sentiment_model.pkl
                              │                         ├── tfidf_vectorizer.pkl
                              │                         └── label_encoder.pkl
                              │
                       ┌──────┴──────┐
                       │  public/    │
                       │  index.html │
                       └─────────────┘
```

## Cấu trúc thư mục

```
FinSentiment/
├── backend/
│   ├── public/
│   │   └── index.html          # Giao diện web
│   ├── server.js               # Express server + API proxy
│   ├── package.json
│   └── package-lock.json
├── ml_service/
│   ├── app.py                  # Flask ML service
│   └── requirements.txt        # Python dependencies
├── models/
│   ├── best_sentiment_model.pkl    # Logistic Regression model
│   ├── tfidf_vectorizer.pkl        # TF-IDF vectorizer
│   └── label_encoder.pkl           # Label encoder
├── demo.ipynb                  # Notebook training & evaluation
├── .gitignore
└── README.md
```

## Yêu cầu

| Thành phần | Phiên bản |
| ---------- | --------- |
| Node.js    | >= 18     |
| Python     | >= 3.11   |
| pip        | Latest    |
| npm        | >= 9      |

## Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/<your-username>/FinSentiment.git
cd FinSentiment
```

### 2. Cài đặt Backend (Express.js)

```bash
cd backend
npm install
cd ..
```

### 3. Cài đặt ML Service (Python)

Tạo virtual environment và cài đặt dependencies:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r ml_service/requirements.txt
```

## Cách chạy

Cần chạy **2 service** song song:

### Terminal 1 - ML Service

```bash
# Bật virtual environment (nếu chưa)
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

python ml_service/app.py
```

ML service sẽ chạy tại: `http://localhost:5000`

### Terminal 2 - Backend

```bash
cd backend
npm start
```

Backend sẽ chạy tại: `http://localhost:3000`

### Truy cập ứng dụng

Mở trình duyệt và truy cập: **http://localhost:3000**

Nhập văn bản tiếng Việt vào ô input và nhấn "Phân tích" hoặc dùng `Ctrl+Enter`.

## API Reference

### POST `/api/predict`

Phân tích cảm xúc của văn bản.

**Request:**

```json
{
  "text": "Giá cổ phiếu tăng mạnh hôm nay"
}
```

**Response (200):**

```json
{
  "text": "Giá cổ phiếu tăng mạnh hôm nay",
  "sentiment": "positive",
  "scores": {
    "negative": 0.0512,
    "neutral": 0.1234,
    "positive": 0.8254
  }
}
```

**Response (400):**

```json
{
  "error": "Missing \"text\" field"
}
```

### GET `/health` (ML Service only)

Kiểm tra trạng thái ML service.

```bash
curl http://localhost:5000/health
```

```json
{
  "status": "ok"
}
```

## Pipeline xử lý

### Tiền xử lý văn bản

1. Chuyển về chữ thường
2. Loại bỏ URL, email
3. Loại bỏ ký tự đặc biệt (giữ chữ cái tiếng Việt + số)
4. Tách từ cụm tiếng Việt (word segmentation) bằng `underthesea`
5. Chuẩn hóa khoảng trắng

### Trích xuất đặc trưng

- **Phương pháp**: TF-IDF (Term Frequency - Inverse Document Frequency)
- **Cấu hình**:
  - `max_features`: 15,000
  - `ngram_range`: (1, 2) - unigram + bigram
  - `min_df`: 3 (loại bỏ từ xuất hiện quá ít)
  - `max_df`: 0.9 (loại bỏ từ xuất hiện quá nhiều)
  - `sublinear_tf`: True (logarithmic TF scaling)

### Mô hình phân loại

Ba mô hình được đánh giá:

| Mô hình                 | Accuracy   | Weighted F1 |
| ----------------------- | ---------- | ----------- |
| Linear SVM              | 0.6981     | 0.6988      |
| **Logistic Regression** | **0.7048** | **0.7057**  |
| Multinomial NB          | 0.6867     | 0.6880      |

Mô hình tốt nhất: **Logistic Regression** (chọn dựa trên weighted F1-score).

## Kết quả mô hình

### Classification Report (Logistic Regression)

```
              precision    recall  f1-score   support

    negative       0.69      0.69      0.69       350
     neutral       0.66      0.70      0.68       350
    positive       0.78      0.72      0.75       350

    accuracy                           0.70      1050
   weighted avg       0.71      0.70      0.71      1050
```

## Dataset

- **Nguồn**: [VLSP 2016 Sentiment Analysis](https://huggingface.co/datasets/ura-hcmut/vlsp2016) (HuggingFace)
- **Số mẫu**: 5,100 (train) + 1,050 (test)
- **Phân bố nhãn**: Cân bằng (1,700 positive / 1,700 negative / 1,700 neutral)
- **Độ dài trung bình**: ~130 ký tự / văn bản
- **Ngôn ngữ**: Tiếng Việt

## Demo

File `demo.ipynb` là Jupyter Notebook chứa toàn bộ quy trình:

1. Tải dataset từ HuggingFace
2. Phân tích và kiểm tra chất lượng dataset
3. Tiền xử lý văn bản tiếng Việt
4. Training và so sánh 3 mô hình
5. Lưu mô hình tốt nhất

### Chạy notebook

```bash
# With Jupyter
pip install jupyter datasets matplotlib seaborn
jupyter notebook demo.ipynb

# Or with VS Code
# Mở file demo.ipynb trực tiếp trong VS Code
```

## Đóng góp

Mọi đóng góp đều được đánh giá cao. Để đóng góp:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/your-feature`)
3. Commit thay đổi (`git commit -m 'Add some feature'`)
4. Push lên branch (`git push origin feature/your-feature`)
5. Mở Pull Request

## License

[MIT](LICENSE)
