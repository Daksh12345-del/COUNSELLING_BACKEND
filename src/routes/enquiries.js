const express = require('express');
const rateLimit = require('express-rate-limit');
const pool = require('../db');
const { validateEnquiry } = require('../utils/validate');

const router = express.Router();

// Stops form-spam scripts from hammering the endpoint. Real visitors will never notice.
const enquiryLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 8,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many submissions from this device. Please try again later.' },
});

// POST /api/enquiries — used by the "Free Enquiry" form
router.post('/', enquiryLimiter, async (req, res) => {
  const { errors, data } = validateEnquiry(req.body || {});
  if (errors.length) {
    return res.status(400).json({ error: errors[0], errors });
  }

  try {
    const result = await pool.query(
      `INSERT INTO enquiries (name, phone, email, current_class, stream, course, city, message)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
       RETURNING id, created_at`,
      [data.name, data.phone, data.email || null, data.currentClass || null, data.stream || null,
       data.course || null, data.city || null, data.message || null]
    );
    res.status(201).json({ id: result.rows[0].id, createdAt: result.rows[0].created_at });
  } catch (err) {
    console.error('Failed to save enquiry:', err);
    res.status(500).json({ error: 'Something went wrong saving your enquiry. Please try again or WhatsApp us.' });
  }
});

module.exports = router;
