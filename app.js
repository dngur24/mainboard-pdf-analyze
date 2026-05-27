const express = require('express');
const app = express();
const fs = require('fs');
const path = require('path');

// Load data
const dataPath = path.join(__dirname, 'data', 'motherboards.json');
const mbData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

// Set EJS as view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// API Routes
app.get('/api/motherboards', (req, res) => {
  res.json(mbData);
});

app.get('/api/motherboards/:id', (req, res) => {
  const board = mbData.find(b => b.id === req.params.id);
  if (!board) return res.status(404).json({ error: 'Board not found' });
  res.json(board);
});

// View Routes
app.get('/', (req, res) => {
  res.render('index', { boards: mbData });
});

app.get('/motherboard/:id', (req, res) => {
  const board = mbData.find(b => b.id === req.params.id);
  if (!board) return res.status(404).send('Board not found');
  res.render('details', { board });
});

// Error handling
app.use((req, res) => {
  res.status(404).send('404 Not Found');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
