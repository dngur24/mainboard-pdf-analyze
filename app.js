require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const chokidar = require('chokidar');
const app = express();
const fs = require('fs');
const path = require('path');
const Motherboard = require('./models/Motherboard');

app.use(express.json());

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI)
  .then(() => {
    console.log('Connected to MongoDB Atlas');
    syncData();
  })
  .catch(err => console.error('MongoDB connection error:', err));

// Sync Data from JSON to MongoDB (Upsert)
const dataDir = path.join(__dirname, 'data');
async function syncData() {
  try {
    console.log('🔄 Checking for data synchronization...');
    const files = fs.readdirSync(dataDir);
    let allBoards = [];

    // 1. 모든 JSON 파일 읽기
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
          console.error(`❌ Error parsing ${file}:`, err);
        }
      }
    });

    if (allBoards.length === 0) {
      console.log('ℹ️ No local JSON data found to sync.');
      return;
    }

    // 2. 중복 ID 제거 (로컬 파일 간 중복 방지)
    const uniqueBoards = Array.from(new Map(allBoards.map(item => [item.id, item])).values());
    console.log(`🔍 Unique boards to sync: ${uniqueBoards.length} (${uniqueBoards.map(b => b.id).join(', ')})`);

    // 3. 각 보드별로 Upsert 수행
    let updateCount = 0;
    let insertCount = 0;

    for (const board of uniqueBoards) {
      if (!board.id) {
        console.warn('⚠️ Skipping board with no ID:', board.name);
        continue;
      }

      const result = await Motherboard.findOneAndUpdate(
        { id: board.id },
        board,
        { upsert: true, returnDocument: 'after', includeResultMetadata: true }
      );

      if (result.lastErrorObject && result.lastErrorObject.updatedExisting) {
        updateCount++;
        console.log(`  - [Update] ${board.id}`);
      } else {
        insertCount++;
        console.log(`  - [Insert] ${board.id}`);
      }
    }

    if (insertCount > 0 || updateCount > 0) {
      console.log(`✅ Sync complete: ${insertCount} new boards added, ${updateCount} existing boards updated.`);
    } else {
      console.log('✅ Database is already up to date.');
    }
  } catch (err) {
    console.error('❌ Sync error:', err);
  }
}

// Watch for file changes in data directory
const watcher = chokidar.watch(dataDir, {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true
});

watcher.on('change', (filePath) => {
  if (filePath.endsWith('.json')) {
    console.log(`📝 File ${path.basename(filePath)} changed. Auto-syncing...`);
    syncData();
  }
}).on('add', (filePath) => {
  if (filePath.endsWith('.json')) {
    console.log(`➕ New file ${path.basename(filePath)} detected. Auto-syncing...`);
    syncData();
  }
});

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
