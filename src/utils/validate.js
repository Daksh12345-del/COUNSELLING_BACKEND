// Small, dependency-free validation helpers shared by the public routes.
// Keeps bad/garbage submissions out of the database without needing a heavy validation library.

const PHONE_RE = /^[+]?[\d\s-]{7,16}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function cleanString(value, maxLen) {
  if (value === undefined || value === null) return '';
  const s = String(value).trim();
  return maxLen ? s.slice(0, maxLen) : s;
}

function validateEnquiry(body) {
  const errors = [];
  const name = cleanString(body.name, 120);
  const phone = cleanString(body.phone, 20);
  const email = cleanString(body.email, 150);

  if (name.length < 2) errors.push('Please enter your full name.');
  if (!PHONE_RE.test(phone)) errors.push('Please enter a valid phone number.');
  if (email && !EMAIL_RE.test(email)) errors.push('Please enter a valid email address.');

  const data = {
    name,
    phone,
    email,
    currentClass: cleanString(body.currentClass, 50),
    stream: cleanString(body.stream, 50),
    course: cleanString(body.course, 120),
    city: cleanString(body.city, 100),
    message: cleanString(body.message, 1000),
  };

  return { errors, data };
}

const VALID_SESSION_TYPES = ['Phone Call', 'Google Meet', 'WhatsApp'];

function validateBooking(body) {
  const errors = [];
  const name = cleanString(body.name, 120);
  const phone = cleanString(body.phone, 20);
  const date = cleanString(body.date, 10); // YYYY-MM-DD
  const time = cleanString(body.time, 20);
  const sessionType = cleanString(body.sessionType, 20) || 'Phone Call';

  if (name.length < 2) errors.push('Please enter your full name.');
  if (!PHONE_RE.test(phone)) errors.push('Please enter a valid phone number.');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) errors.push('Please pick a valid day.');
  if (!time) errors.push('Please pick a valid time slot.');
  if (!VALID_SESSION_TYPES.includes(sessionType)) errors.push('Invalid session type.');

  if (/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    const todayStr = new Date().toISOString().slice(0, 10);
    if (date < todayStr) errors.push('That date has already passed.');
  }

  const data = {
    name,
    phone,
    sessionType,
    date,
    dayLabel: cleanString(body.dayLabel, 50),
    time,
    stream: cleanString(body.stream, 50),
    course: cleanString(body.course, 120),
  };

  return { errors, data };
}

module.exports = { validateEnquiry, validateBooking };
