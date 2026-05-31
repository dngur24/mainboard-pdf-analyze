const mongoose = require('mongoose');

const SlotSchema = new mongoose.Schema({
  id: String,
  name: String,
  type: String,
  source: String
});

const StorageSchema = new mongoose.Schema({
  id: String,
  name: String,
  type: String,
  source: String
});

const SharingRuleSchema = new mongoose.Schema({
  trigger: String,
  impact: String,
  effect: String,
  newSpeed: String,
  description: String
});

const MotherboardSchema = new mongoose.Schema({
  id: { type: String, required: true, unique: true },
  name: { type: String, required: true },
  chipset: String,
  slots: [SlotSchema],
  storage: [StorageSchema],
  sharingRules: [SharingRuleSchema]
});

module.exports = mongoose.model('Motherboard', MotherboardSchema);
