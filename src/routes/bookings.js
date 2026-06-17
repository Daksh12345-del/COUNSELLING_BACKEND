const express = require('express');
const rateLimit = require('express-rate-limit');
const pool = require('../db');
const { validateBooking } = require('../utils/validate');

const router = express.Router();

const bookingLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 8,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many booking attempts from this device. Please try again later.' },
});

// GET /api/bookings/availability?date=YYYY-MM-DD
// Returns which time slots are already taken on that day, so the frontend can grey them out.
router.get('/availability', async (req, res) => {
  const date = String(req.query.date || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return res.status(400).json({ error: 'Invalid date format. Expected YYYY-MM-DD.' });
  }
  try {
    const result = await pool.query(
      `SELECT time_slot FROM bookings WHERE booking_date = $1 AND status <> 'Cancelled'`,
      [date]
    );
    res.json({ date, bookedTimes: result.rows.map((r) => r.time_slot) });
  } catch (err) {
    console.error('Failed to fetch availability:', err);
    res.status(500).json({ error: 'Could not load availability right now.' });
  }
});

// POST /api/bookings — used by the "Schedule Free Call" widget
router.post('/', bookingLimiter, async (req, res) => {
  const { errors, data } = validateBooking(req.body || {});
  if (errors.length) {
    return res.status(400).json({ error: errors[0], errors });
  }

  try {
    const result = await pool.query(
      `INSERT INTO bookings (name, phone, session_type, booking_date, day_label, time_slot, stream, course)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
       RETURNING id, created_at`,
      [data.name, data.phone, data.sessionType, data.date, data.dayLabel || null, data.time,
       data.stream || null, data.course || null]
    );
    res.status(201).json({ id: result.rows[0].id, createdAt: result.rows[0].created_at });
  } catch (err) {
    // The partial unique index (booking_date, time_slot) raises code 23505 on a clash
    if (err.code === '23505') {
      return res.status(409).json({ error: 'That slot was just taken by someone else. Please pick another time.' });
    }
    console.error('Failed to save booking:', err);
    res.status(500).json({ error: 'Something went wrong booking your call. Please try again or WhatsApp us.' });
  }
});

module.exports = router;
