
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');

const upload = multer({ storage: multer.memoryStorage() });
const router = express.Router();
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

router.post('/analyze', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: 'file required' });

    const form = new FormData();
    form.append('file', req.file.buffer, {
      filename: req.file.originalname || 'upload.jpg',
      contentType: req.file.mimetype || 'application/octet-stream',
      knownLength: req.file.size,
    });

    const aiResp = await axios.post(`${AI_SERVICE_URL}/analyze`, form, {
      headers: { ...form.getHeaders() },
      maxBodyLength: Infinity,
      timeout: 30000
    });

    return res.status(aiResp.status).json(aiResp.data);
  } catch (err) {
    console.error('AI proxy error:', err.message || err);
    return res.status(500).json({ error: 'AI proxy failed' });
  }
});

module.exports = router;
