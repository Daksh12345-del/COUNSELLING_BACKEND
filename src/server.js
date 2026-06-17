require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const enquiriesRoute = require('./routes/enquiries');
const bookingsRoute = require('./routes/bookings');
const adminRoute = require('./routes/admin');

const app = express();

app.use(helmet());
app.use(express.json({ limit: '100kb' }));

const allowedOrigins = (process.env.ALLOWED_ORIGINS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

app.use(cors({
  origin(origin, callback) {
    // Allow requests with no origin (curl, server-to-server, Postman) and any configured origin
    if (!origin || allowedOrigins.length === 0 || allowedOrigins.includes(origin)) {
      return callback(null, true);
    }
    return callback(new Error('Not allowed by CORS'));
  },
}));

app.get('/api/health', (req, res) => res.json({ ok: true }));

app.use('/api/enquiries', enquiriesRoute);
app.use('/api/bookings', bookingsRoute);
app.use('/api/admin', adminRoute);

// Fallback error handler (e.g. CORS rejection, bad JSON body)
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({ error: err.message || 'Something went wrong.' });
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`Sarvpratham backend listening on port ${PORT}`);
});
