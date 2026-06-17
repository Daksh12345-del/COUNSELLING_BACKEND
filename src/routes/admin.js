const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const rateLimit = require('express-rate-limit');
const pool = require('../db');
const { requireAdmin } = require('../middleware/auth');

const router = express.Router();

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many login attempts. Please wait a few minutes and try again.' },
});

// ===== AUTH =====
// POST /api/admin/login
router.post('/login', loginLimiter, async (req, res) => {
  const username = String(req.body?.username || '').trim();
  const password = String(req.body?.password || '');
  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password are required.' });
  }

  try {
    const result = await pool.query('SELECT id, username, password_hash FROM admin_users WHERE username = $1', [username]);
    const user = result.rows[0];
    // Always run bcrypt.compare even if user is missing, so login timing doesn't reveal valid usernames.
    const hash = user ? user.password_hash : '$2a$12$invalidsaltinvalidsaltinvalidsaltinvalidsaltinvalid';
    const ok = await bcrypt.compare(password, hash);

    if (!user || !ok) {
      return res.status(401).json({ error: 'Incorrect username or password.' });
    }

    const token = jwt.sign(
      { sub: user.id, username: user.username },
      process.env.JWT_SECRET,
      { expiresIn: process.env.JWT_EXPIRES_IN || '12h' }
    );
    res.json({ token, expiresIn: process.env.JWT_EXPIRES_IN || '12h' });
  } catch (err) {
    console.error('Login failed:', err);
    res.status(500).json({ error: 'Login is temporarily unavailable.' });
  }
});

// GET /api/admin/me — lets the frontend check if a stored token is still valid
router.get('/me', requireAdmin, (req, res) => {
  res.json({ username: req.admin.username });
});

// ===== STATS =====
// GET /api/admin/stats
router.get('/stats', requireAdmin, async (req, res) => {
  try {
    const [totals, streams, courses] = await Promise.all([
      pool.query(`
        SELECT
          (SELECT COUNT(*) FROM enquiries) AS total_enquiries,
          (SELECT COUNT(*) FROM enquiries WHERE status = 'New') AS new_enquiries,
          (SELECT COUNT(*) FROM enquiries WHERE status = 'Enrolled') AS enrolled_enquiries,
          (SELECT COUNT(*) FROM bookings WHERE status <> 'Cancelled') AS total_bookings
      `),
      pool.query(`
        SELECT COALESCE(stream, 'Not specified') AS stream, COUNT(*) AS count
        FROM enquiries GROUP BY stream ORDER BY count DESC
      `),
      pool.query(`
        SELECT COALESCE(course, 'Not specified') AS course, COUNT(*) AS count
        FROM enquiries GROUP BY course ORDER BY count DESC
      `),
    ]);

    const t = totals.rows[0];
    res.json({
      totalEnquiries: Number(t.total_enquiries),
      newEnquiries: Number(t.new_enquiries),
      enrolledEnquiries: Number(t.enrolled_enquiries),
      totalBookings: Number(t.total_bookings),
      streamBreakdown: streams.rows.map((r) => ({ stream: r.stream, count: Number(r.count) })),
      courseBreakdown: courses.rows.map((r) => ({ course: r.course, count: Number(r.count) })),
    });
  } catch (err) {
    console.error('Failed to load stats:', err);
    res.status(500).json({ error: 'Could not load dashboard stats.' });
  }
});

// ===== ENQUIRIES =====
// GET /api/admin/enquiries?search=&status=&page=&pageSize=
router.get('/enquiries', requireAdmin, async (req, res) => {
  const search = String(req.query.search || '').trim();
  const status = String(req.query.status || '').trim();
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 25));
  const offset = (page - 1) * pageSize;

  const conditions = [];
  const params = [];

  if (search) {
    params.push(`%${search}%`);
    conditions.push(`(name ILIKE $${params.length} OR phone ILIKE $${params.length} OR email ILIKE $${params.length} OR city ILIKE $${params.length} OR course ILIKE $${params.length})`);
  }
  if (status) {
    params.push(status);
    conditions.push(`status = $${params.length}`);
  }
  const whereClause = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

  try {
    const countResult = await pool.query(`SELECT COUNT(*) FROM enquiries ${whereClause}`, params);
    const dataResult = await pool.query(
      `SELECT * FROM enquiries ${whereClause} ORDER BY created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`,
      [...params, pageSize, offset]
    );
    res.json({ total: Number(countResult.rows[0].count), page, pageSize, data: dataResult.rows });
  } catch (err) {
    console.error('Failed to fetch enquiries:', err);
    res.status(500).json({ error: 'Could not load enquiries.' });
  }
});

const VALID_ENQUIRY_STATUSES = ['New', 'Contacted', 'Enrolled', 'Not interested'];

// PATCH /api/admin/enquiries/:id  { status }
router.patch('/enquiries/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const status = String(req.body?.status || '');
  if (!VALID_ENQUIRY_STATUSES.includes(status)) {
    return res.status(400).json({ error: 'Invalid status value.' });
  }
  try {
    const result = await pool.query('UPDATE enquiries SET status = $1 WHERE id = $2 RETURNING *', [status, id]);
    if (!result.rows.length) return res.status(404).json({ error: 'Enquiry not found.' });
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Failed to update enquiry:', err);
    res.status(500).json({ error: 'Could not update enquiry.' });
  }
});

// DELETE /api/admin/enquiries/:id
router.delete('/enquiries/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try {
    const result = await pool.query('DELETE FROM enquiries WHERE id = $1', [id]);
    if (!result.rowCount) return res.status(404).json({ error: 'Enquiry not found.' });
    res.status(204).end();
  } catch (err) {
    console.error('Failed to delete enquiry:', err);
    res.status(500).json({ error: 'Could not delete enquiry.' });
  }
});

// GET /api/admin/enquiries/export — CSV download of everything matching current filters
router.get('/enquiries-export', requireAdmin, async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM enquiries ORDER BY created_at DESC');
    const headers = ['#', 'Date', 'Name', 'Phone', 'Email', 'Class', 'Stream', 'Course', 'City', 'Message', 'Status'];
    const escapeCsv = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = result.rows.map((r, i) => [
      i + 1, r.created_at, r.name, r.phone, r.email, r.current_class, r.stream, r.course, r.city, r.message, r.status,
    ].map(escapeCsv).join(','));
    const csv = [headers.join(','), ...rows].join('\n');

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename="enquiries_${new Date().toISOString().slice(0, 10)}.csv"`);
    res.send(csv);
  } catch (err) {
    console.error('Failed to export enquiries:', err);
    res.status(500).json({ error: 'Could not export enquiries.' });
  }
});

// ===== BOOKINGS =====
// GET /api/admin/bookings?page=&pageSize=
router.get('/bookings', requireAdmin, async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 25));
  const offset = (page - 1) * pageSize;

  try {
    const countResult = await pool.query('SELECT COUNT(*) FROM bookings');
    const dataResult = await pool.query(
      'SELECT * FROM bookings ORDER BY created_at DESC LIMIT $1 OFFSET $2',
      [pageSize, offset]
    );
    res.json({ total: Number(countResult.rows[0].count), page, pageSize, data: dataResult.rows });
  } catch (err) {
    console.error('Failed to fetch bookings:', err);
    res.status(500).json({ error: 'Could not load bookings.' });
  }
});

const VALID_BOOKING_STATUSES = ['Confirmed', 'Completed', 'Cancelled', 'No-show'];

// PATCH /api/admin/bookings/:id  { status }
router.patch('/bookings/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const status = String(req.body?.status || '');
  if (!VALID_BOOKING_STATUSES.includes(status)) {
    return res.status(400).json({ error: 'Invalid status value.' });
  }
  try {
    const result = await pool.query('UPDATE bookings SET status = $1 WHERE id = $2 RETURNING *', [status, id]);
    if (!result.rows.length) return res.status(404).json({ error: 'Booking not found.' });
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Failed to update booking:', err);
    res.status(500).json({ error: 'Could not update booking.' });
  }
});

// DELETE /api/admin/bookings/:id
router.delete('/bookings/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try {
    const result = await pool.query('DELETE FROM bookings WHERE id = $1', [id]);
    if (!result.rowCount) return res.status(404).json({ error: 'Booking not found.' });
    res.status(204).end();
  } catch (err) {
    console.error('Failed to delete booking:', err);
    res.status(500).json({ error: 'Could not delete booking.' });
  }
});

module.exports = router;
