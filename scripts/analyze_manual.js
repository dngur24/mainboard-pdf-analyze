const { GoogleGenerativeAI } = require("@google/generative-ai");
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Initialize Gemini API
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "YOUR_API_KEY_HERE");

async function analyzeManual(manualText) {
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

  const prompt = `
    You are a PC hardware expert. Analyze the following motherboard specification text and extract PCIe lane and M.2 storage information, including bandwidth sharing rules.
    
    Format the output as a JSON object matching this schema:
    {
      "id": "kebab-case-id",
      "name": "Full Motherboard Name",
      "chipset": "Chipset Name",
      "slots": [
        { "id": "pci_1", "name": "Slot Name", "type": "PCIe Version and Lanes", "source": "CPU or Chipset" }
      ],
      "storage": [
        { "id": "m2_1", "name": "M.2 Name", "type": "PCIe Version and Lanes", "source": "CPU or Chipset" }
      ],
      "sharingRules": [
        {
          "trigger": "id_of_m2_that_causes_sharing",
          "impact": "id_of_pci_slot_affected",
          "effect": "disabled OR reduced",
          "newSpeed": "New speed if reduced (optional)",
          "description": "User-friendly description in Korean"
        }
      ]
    }

    Text to analyze:
    ${manualText}

    Return ONLY the raw JSON.
  `;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    let text = response.text();
    
    // Clean JSON output (remove markdown blocks if present)
    text = text.replace(/```json|```/g, "").trim();
    
    const mbJson = JSON.parse(text);
    return mbJson;
  } catch (error) {
    console.error("Analysis failed:", error);
    return null;
  }
}

// Example usage (Internal testing)
if (require.main === module) {
  const sampleText = `
    ROG STRIX X670E-E GAMING WIFI
    AMD X670 Chipset
    Expansion Slots:
    1 x PCIe 5.0 x16 slot (supports x16 mode) [CPU]
    1 x PCIe 5.0 x16 slot (supports x8 mode) [CPU]
    1 x PCIe 4.0 x16 slot (supports x4 mode) [Chipset]
    Storage:
    M.2_1 slot (Key M), type 2242/2260/2280 (supports PCIe 5.0 x4 mode) [CPU]
    M.2_2 slot (Key M), type 2242/2260/2280 (supports PCIe 5.0 x4 mode) [CPU]
    M.2_3 slot (Key M), type 2242/2260/2280 (supports PCIe 5.0 x4 mode) [CPU]
    * M.2_3 shares bandwidth with PCIEX16_1. When M.2_3 is enabled, PCIEX16_1 will run x8 only.
  `;
  
  console.log("Analyzing sample text...");
  analyzeManual(sampleText).then(data => {
    if (data) {
      console.log("Analysis Result:");
      console.log(JSON.stringify(data, null, 2));
    }
  });
}

module.exports = { analyzeManual };
