const express = require('express');
const path = require('path');

const app = express();
const PORT = 3000;
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

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
