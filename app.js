require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const app = express();
const fs = require('fs');
const path = require('path');
const Motherboard = require('./models/Motherboard');

app.use(express.json());

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI)
  .then(() => {
    console.log('Connected to MongoDB Atlas');
    migrateData();
  })
  .catch(err => console.error('MongoDB connection error:', err));

// Data Migration from JSON to MongoDB
const dataDir = path.join(__dirname, 'data');
async function migrateData() {
  try {
    const count = await Motherboard.countDocuments();
    if (count > 0) {
      console.log('Database already has data. Skipping migration.');
      return;
    }

    console.log('Starting data migration from JSON files...');
    const files = fs.readdirSync(dataDir);
    let allBoards = [];

    files.forEach(file => {
      if (file.endsWith('.json')) {
        try {
          const filePath = path.join(dataDir, file);
          const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
          if (Array.isArray(content)) {
            allBoards = allBoards.concat(content);
          } else if (typeof content === 'object' && content !== null) {
            allBoards.push(content);
          }
        } catch (err) {
          console.error(`Error parsing ${file}:`, err);
        }
      }
    });

    if (allBoards.length > 0) {
      // Remove duplicates by ID before inserting
      const uniqueBoards = Array.from(new Map(allBoards.map(item => [item.id, item])).values());
      await Motherboard.insertMany(uniqueBoards);
      console.log(`Successfully migrated ${uniqueBoards.length} boards to MongoDB.`);
    }
  } catch (err) {
    console.error('Migration error:', err);
  }
}

// Set EJS as view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// API Routes
app.get('/api/motherboards', async (req, res) => {
  try {
    const boards = await Motherboard.find();
    res.json(boards);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/motherboards/:id', async (req, res) => {
  try {
    const board = await Motherboard.findOne({ id: req.params.id });
    if (!board) return res.status(404).json({ error: 'Board not found' });
    res.json(board);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST: Register new motherboard
app.post('/api/motherboards', async (req, res) => {
  try {
    const newBoard = new Motherboard(req.body);
    const savedBoard = await newBoard.save();
    res.status(201).json(savedBoard);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// PUT: Update existing motherboard
app.put('/api/motherboards/:id', async (req, res) => {
  try {
    const updatedBoard = await Motherboard.findOneAndUpdate(
      { id: req.params.id },
      req.body,
      { new: true, runValidators: true }
    );
    if (!updatedBoard) return res.status(404).json({ error: 'Board not found' });
    res.json(updatedBoard);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// View Routes
app.get('/', async (req, res) => {
  try {
    const boards = await Motherboard.find();
    res.render('index', { boards });
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.get('/motherboard/:id', async (req, res) => {
  try {
    const board = await Motherboard.findOne({ id: req.params.id });
    if (!board) return res.status(404).send('Board not found');
    res.render('details', { board });
  } catch (err) {
    res.status(500).send(err.message);
  }
});

// Error handling
app.use((req, res) => {
  res.status(404).send('404 Not Found');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
