// Creates (or resets the password of) the admin account used to log into the dashboard.
// Reads ADMIN_USERNAME and ADMIN_PASSWORD from .env
// Usage: npm run create-admin
const bcrypt = require('bcryptjs');
const pool = require('./db');

async function createAdmin() {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;

  if (!username || !password) {
    console.error('Set ADMIN_USERNAME and ADMIN_PASSWORD in your .env file first.');
    process.exit(1);
  }
  if (password.length < 8) {
    console.error('Choose an ADMIN_PASSWORD that is at least 8 characters long.');
    process.exit(1);
  }

  const passwordHash = await bcrypt.hash(password, 12);

  await pool.query(
    `INSERT INTO admin_users (username, password_hash)
     VALUES ($1, $2)
     ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash`,
    [username, passwordHash]
  );

  console.log(`Admin account ready for username "${username}".`);
  console.log('You can now remove ADMIN_PASSWORD from your .env file if you like — it is only read by this script.');
  await pool.end();
}

createAdmin().catch((err) => {
  console.error('Failed to create admin user:', err);
  process.exit(1);
});
