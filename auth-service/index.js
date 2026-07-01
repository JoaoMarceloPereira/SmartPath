const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { Pool } = require('pg');

const app = express();
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || 'super_secret_smartpath_key';
const PORT = process.env.PORT || 8082;

// Database connection
const pool = new Pool({
  user: process.env.PGUSER || 'smartpath',
  host: process.env.PGHOST || 'postgres',
  database: process.env.PGDATABASE || 'smartpath',
  password: process.env.PGPASSWORD || 'smartpath123',
  port: process.env.PGPORT || 5432,
});

// Setup table if not exists
pool.query(`
  CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'USER'
  );
`).catch(err => console.error("DB Setup Error:", err));

app.post('/auth/register', async (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) return res.status(400).json({ error: 'Username and password required' });
  
  try {
    const salt = await bcrypt.genSalt(10);
    const hash = await bcrypt.hash(password, salt);
    const result = await pool.query('INSERT INTO users (username, password) VALUES ($1, $2) RETURNING id, username, role', [username, hash]);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    if (err.code === '23505') return res.status(409).json({ error: 'User already exists' });
    res.status(500).json({ error: 'Internal error' });
  }
});

app.post('/auth/login', async (req, res) => {
  const { username, password } = req.body;
  
  try {
    const result = await pool.query('SELECT * FROM users WHERE username = $1', [username]);
    if (result.rows.length === 0) return res.status(401).json({ error: 'Invalid credentials' });
    
    const user = result.rows[0];
    const isMatch = await bcrypt.compare(password, user.password);
    
    if (!isMatch) return res.status(401).json({ error: 'Invalid credentials' });
    
    const token = jwt.sign({ id: user.id, username: user.username, role: user.role }, JWT_SECRET, { expiresIn: '1h' });
    res.json({ token });
  } catch (err) {
    res.status(500).json({ error: 'Internal error' });
  }
});

app.post('/auth/validate', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ valid: false, error: 'No token provided' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    res.json({ valid: true, user: decoded });
  } catch (err) {
    res.status(401).json({ valid: false, error: 'Invalid or expired token' });
  }
});

app.get('/health', (req, res) => res.json({ status: 'UP' }));

app.listen(PORT, () => console.log(`Auth Service running on port ${PORT}`));
