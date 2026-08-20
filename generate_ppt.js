const pptxgen = require('pptxgenjs');

let pptx = new pptxgen();
pptx.layout = 'LAYOUT_16x9';

// ---------------------------------------------------------
// THEME: "NEON DARK GLASS" - Extremely premium tech aesthetic
// ---------------------------------------------------------
const C = {
    bg: "0F172A",          // Very dark slate
    cardBg: "1E293B",      // Lighter slate for blocks
    accent1: "3B82F6",     // Brilliant Blue
    accent2: "10B981",     // Neon Emerald
    accent3: "F43F5E",     // Rose/Red for problems
    accent4: "F59E0B",     // Amber
    textMain: "F8FAFC",    // White
    textMuted: "94A3B8"    // Gray
};

// MASTER SLIDES
pptx.defineSlideMaster({
    title: "DARK_TITLE",
    background: { color: C.bg },
    objects: [
        { rect: { x: 0, y: 0, w: '100%', h: 0.1, fill: { color: C.accent1 } } },
        { line: { x: 0, y: '50%', w: '100%', h: 0, line: { color: "1E293B", width: 1 } } },
        { line: { x: '50%', y: 0, w: 0, h: '100%', line: { color: "1E293B", width: 1 } } },
        { text: { text: "TEAM VISIONARIES", options: { x: 0.5, y: '90%', w: 4, h: 0.5, color: C.accent2, fontFace: "Helvetica Neue", fontSize: 14, bold: true, letterSpacing: 0.1 } } },
        { text: { text: "Hexaware Mavericks Hackathon 2026", options: { x: '65%', y: '90%', w: 3.5, h: 0.5, color: C.textMuted, fontFace: "Helvetica Neue", fontSize: 12, align: "right" } } }
    ]
});

pptx.defineSlideMaster({
    title: "DARK_CONTENT",
    background: { color: C.bg },
    objects: [
        { rect: { x: 0, y: 0, w: '8%', h: '100%', fill: { color: "0B1120" } } }, // Sidebar
        { text: { text: "VISIONARIES", options: { x: -3.6, y: 3.5, w: 8, h: 0.5, color: "1E293B", fontFace: "Arial Black", fontSize: 40, rotate: 270, align: "center" } } },
        { rect: { x: '8%', y: 0, w: '92%', h: 0.05, fill: { color: C.accent1 } } }
    ]
});

// Helper for beautiful block cards
function addCard(slide, x, y, w, h, title, text, accentColor) {
    slide.addShape(pptx.ShapeType.roundRect, { x: x, y: y, w: w, h: h, fill: { color: C.cardBg }, rectRadius: 0.1 });
    slide.addShape(pptx.ShapeType.rect, { x: x, y: y, w: w, h: 0.1, fill: { color: accentColor } });
    slide.addText(title, { x: x+0.2, y: y+0.3, w: w-0.4, h: 0.4, color: accentColor, fontSize: 16, bold: true, fontFace: "Helvetica Neue" });
    slide.addText(text, { x: x+0.2, y: y+0.8, w: w-0.4, h: h-1.0, color: C.textMain, fontSize: 13, fontFace: "Helvetica Neue", align: "left", valign: "top" });
}

function addTitle(slide, main, sub) {
    slide.addText(main, { x: 1.0, y: 0.3, w: 8.5, h: 0.6, fontSize: 32, fontFace: "Helvetica Neue", bold: true, color: C.textMain });
    if(sub) slide.addText(sub, { x: 1.0, y: 0.9, w: 8.5, h: 0.4, fontSize: 16, color: C.textMuted });
}

// ==========================================
// SLIDE 1: HERO TITLE
// ==========================================
let slide1 = pptx.addSlide({ masterName: "DARK_TITLE" });
slide1.addShape(pptx.ShapeType.rect, { x: 0, y: '35%', w: '100%', h: '30%', fill: { color: "0B1120" } });
slide1.addText("SYNAPSE-KG", { x: 0, y: '36%', w: '100%', h: 1.5, fontSize: 72, fontFace: "Helvetica Neue", bold: true, color: C.textMain, align: "center", letterSpacing: 0.05 });
slide1.addText("Neuro-Symbolic Clinical Trial Matching Engine", { x: 0, y: '52%', w: '100%', h: 0.6, fontSize: 24, fontFace: "Helvetica Neue", color: C.accent1, align: "center" });
slide1.addImage({ x: 3.5, y: 0.5, w: 3, h: 1.5, path: "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=500&q=80", sizing: { type: "crop" } });

// ==========================================
// SLIDE 2: THE CLINICAL CONTEXT
// ==========================================
let slide2 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide2, "The Critical Medical Bottleneck", "Over 80% of clinical trials are delayed due to patient recruitment failures.");
slide2.addShape(pptx.ShapeType.rect, { x: 1.0, y: 1.6, w: 8.5, h: 3.0, fill: { color: C.cardBg } });
slide2.addText("A breakthrough drug cannot reach the market if it cannot find the right patients.", { x: 1.2, y: 2.0, w: 8.0, h: 1.0, fontSize: 24, color: C.accent1, bold: true, align: "center" });
slide2.addText("Identifying eligible candidates requires cross-referencing hundreds of strict inclusion/exclusion criteria against massive, unstructured medical histories. It is the most expensive and time-consuming phase of clinical research.", { x: 1.5, y: 2.8, w: 7.4, h: 1.5, fontSize: 16, color: C.textMain, align: "center" });

// ==========================================
// SLIDE 3: PROBLEM 1 (HUMAN LIMIT)
// ==========================================
let slide3 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide3, "Problem 1: The Human Bottleneck", "Manual chart review is fundamentally unscalable.");
addCard(slide3, 1.0, 1.8, 4.0, 3.0, "Hours Per Patient", "Clinical Research Coordinators (CRCs) spend up to 4 hours manually reading through a single patient's EHR to determine trial eligibility.", C.accent3);
addCard(slide3, 5.5, 1.8, 4.0, 3.0, "The Unstructured Data Trap", "80% of medical data (Doctor's notes, imaging reports) is unstructured text. Keyword searching misses crucial context and nuance.", C.accent3);

// ==========================================
// SLIDE 4: PROBLEM 2 (AI LIABILITY)
// ==========================================
let slide4 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide4, "Problem 2: The Hallucination Liability", "Why hasn't Generative AI solved this yet?");
addCard(slide4, 1.0, 1.8, 8.5, 1.8, "LLMs Fail at Math and Logic", "Generative AI predicts the next most likely token. It cannot be trusted to definitively compute whether 'Creatinine 1.6 mg/dL' satisfies a strict '< 1.5' inclusion criteria.", C.accent3);
addCard(slide4, 1.0, 3.8, 8.5, 1.2, "Zero Margin for Error", "A hallucinated trial inclusion places a patient's life at risk and can invalidate millions of dollars of clinical efficacy data.", C.accent4);

// ==========================================
// SLIDE 5: PROBLEM 3 (PRIVACY)
// ==========================================
let slide5 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide5, "Problem 3: The Privacy Roadblock", "Medical data cannot leave the hospital walls.");
addCard(slide5, 1.0, 1.8, 4.0, 3.0, "HIPAA Violations", "Sending raw patient health information (PHI) to external cloud LLM providers (like OpenAI or Groq) is a massive regulatory violation.", C.accent3);
addCard(slide5, 5.5, 1.8, 4.0, 3.0, "The Sanitization Gap", "Hospitals cannot leverage advanced AI until they can guarantee that no names, SSNs, or locations ever reach the model.", C.accent3);

// ==========================================
// SLIDE 6: THE SOLUTION
// ==========================================
let slide6 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide6, "Our Solution: Synapse-KG", "A True Neuro-Symbolic Architecture.");
slide6.addShape(pptx.ShapeType.rect, { x: 1.0, y: 1.6, w: 8.5, h: 3.2, fill: { color: C.cardBg }, line: { color: C.accent2, width: 2 } });
slide6.addText("Divide and Conquer", { x: 1.0, y: 1.8, w: 8.5, h: 0.6, fontSize: 28, color: C.accent2, bold: true, align: "center" });
slide6.addText("We use strict Mathematical Logic (Symbolic AI) to make the life-or-death decisions.\n\nWe use Generative LLMs (Neural AI) strictly to read the math and explain it to humans in plain English.", { x: 1.5, y: 2.6, w: 7.5, h: 1.5, fontSize: 18, color: C.textMain, align: "center" });

// ==========================================
// SLIDE 7: FULL PIPELINE ARCHITECTURE
// ==========================================
let slide7 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide7, "End-to-End System Architecture", "Data Flow from Raw EHR to RAG Explanation.");

let yF = 2.0;
// Row 1
slide7.addShape(pptx.ShapeType.roundRect, { x: 1.0, y: yF, w: 1.4, h: 0.8, fill: { color: "1E3A8A" } });
slide7.addText("1. Raw EHR\nFHIR Data", { x: 1.0, y: yF+0.1, w: 1.4, h: 0.6, align: "center", color: C.textMain, fontSize: 11, bold: true });

slide7.addShape(pptx.ShapeType.rightArrow, { x: 2.5, y: yF+0.3, w: 0.4, h: 0.2, fill: { color: C.accent1 } });

slide7.addShape(pptx.ShapeType.roundRect, { x: 3.0, y: yF, w: 1.6, h: 0.8, fill: { color: C.accent3 } });
slide7.addText("2. Presidio\nPII Scrubbing", { x: 3.0, y: yF+0.1, w: 1.6, h: 0.6, align: "center", color: C.textMain, fontSize: 11, bold: true });

slide7.addShape(pptx.ShapeType.rightArrow, { x: 4.7, y: yF+0.3, w: 0.4, h: 0.2, fill: { color: C.accent1 } });

slide7.addShape(pptx.ShapeType.roundRect, { x: 5.2, y: yF, w: 1.8, h: 0.8, fill: { color: "064E3B" } });
slide7.addText("3. ClinicalTrials\nAST Parser", { x: 5.2, y: yF+0.1, w: 1.8, h: 0.6, align: "center", color: C.textMain, fontSize: 11, bold: true });

// Row 2
slide7.addShape(pptx.ShapeType.downArrow, { x: 6.0, y: yF+0.9, w: 0.2, h: 0.4, fill: { color: C.accent2 } });

slide7.addShape(pptx.ShapeType.roundRect, { x: 5.2, y: yF+1.4, w: 1.8, h: 0.8, fill: { color: "064E3B" } });
slide7.addText("4. NetworkX\nKnowledge Graph", { x: 5.2, y: yF+1.5, w: 1.8, h: 0.6, align: "center", color: C.textMain, fontSize: 11, bold: true });

slide7.addShape(pptx.ShapeType.leftArrow, { x: 4.7, y: yF+1.7, w: 0.4, h: 0.2, fill: { color: C.accent2 } });

slide7.addShape(pptx.ShapeType.roundRect, { x: 2.8, y: yF+1.4, w: 1.8, h: 0.8, fill: { color: "064E3B" } });
slide7.addText("5. AST Math\nExecution", { x: 2.8, y: yF+1.5, w: 1.8, h: 0.6, align: "center", color: C.textMain, fontSize: 11, bold: true });

slide7.addShape(pptx.ShapeType.downArrow, { x: 3.6, y: yF+2.3, w: 0.2, h: 0.4, fill: { color: C.accent1 } });

// Row 3
slide7.addShape(pptx.ShapeType.roundRect, { x: 2.0, y: yF+2.8, w: 3.4, h: 0.8, fill: { color: C.accent1 } });
slide7.addText("6. GraphRAG Explainability\n(Groq Llama-3)", { x: 2.0, y: yF+2.9, w: 3.4, h: 0.6, align: "center", color: C.textMain, fontSize: 12, bold: true });

slide7.addShape(pptx.ShapeType.rightArrow, { x: 5.5, y: yF+3.1, w: 0.4, h: 0.2, fill: { color: C.accent1 } });

slide7.addShape(pptx.ShapeType.roundRect, { x: 6.0, y: yF+2.8, w: 3.0, h: 0.8, fill: { color: C.cardBg }, line: { color: C.textMain, width: 2 } });
slide7.addText("7. React Dynamic\nDashboard", { x: 6.0, y: yF+2.9, w: 3.0, h: 0.6, align: "center", color: C.accent1, fontSize: 12, bold: true });

// ==========================================
// SLIDE 8: PHASE 1 (PRESIDIO)
// ==========================================
let slide8 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide8, "Phase 1: Zero-Trust Ingestion", "Complete Local PII Scrubbing.");
addCard(slide8, 1.0, 1.8, 8.5, 3.0, "Microsoft Presidio Integration", "Every doctor's note and unstructured string is routed through our local PresidioService before hitting the database or AI.\n\n• Uses advanced spaCy NLP models.\n• Automatically detects and replaces Names, SSNs, Dates, and Locations with safe tags (e.g., [PERSON_1]).\n• Ensures 100% HIPAA Compliance natively.", C.accent1);

// ==========================================
// SLIDE 9: PHASE 2 (AST ENGINE)
// ==========================================
let slide9 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide9, "Phase 2: Abstract Syntax Trees (AST)", "Turning English into strict computation.");
addCard(slide9, 1.0, 1.8, 8.5, 3.0, "Deterministic Math", "We use an LLM exclusively for extraction, pulling variables out of clinicaltrials.gov and structuring them into an AST.\n\nExample Text: 'Must have Creatinine < 1.5 mg/dL'\nAST Node: { Target: 'Creatinine', Operator: '<', Value: 1.5 }\n\nDuring screening, Python executes this math. It cannot hallucinate a pass.", C.accent2);

// ==========================================
// SLIDE 10: PHASE 3 (GRAPH)
// ==========================================
let slide10 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide10, "Phase 3: NetworkX Knowledge Graph", "Topological view of the patient.");
addCard(slide10, 1.0, 1.8, 8.5, 3.0, "Dynamic Entity Resolution", "A patient isn't a flat table. We construct a directed graph where Nodes = (Patient, Condition, Lab, Medication) and Edges = (HAS_CONDITION, OBSERVED_LAB).\n\nThis graph is rendered natively as an interactive physics simulation in our React Dashboard using PyVis, giving clinicians an instant holistic view.", C.accent1);

// ==========================================
// SLIDE 11: PHASE 4 (GraphRAG)
// ==========================================
let slide11 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide11, "Phase 4: Execution & GraphRAG", "Explainable AI without the risk.");
addCard(slide11, 1.0, 1.8, 8.5, 3.0, "The Groq Translation Layer", "1. The AST Engine executes against the Knowledge Graph, yielding binary traces (MET, NOT_MET).\n2. We bundle these deterministic traces and the graph topology.\n3. We send this strict context to Groq (Llama-3).\n4. The LLM translates the math into a human-readable medical rationale.", C.accent1);

// ==========================================
// SLIDE 12: PHASE 5 (DYNAMIC SIMULATION)
// ==========================================
let slide12 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide12, "Phase 5: The Feedback Loop", "Dynamic Real-Time Simulation.");
addCard(slide12, 1.0, 1.8, 8.5, 3.0, "Live FHIR / HL7 Webhooks", "The real world isn't static. What happens when a patient's new blood test drops?\n\nOur system listens for live data streams. When a new lab result arrives, it instantly mutates the Knowledge Graph. The AST Engine instantly re-fires, and a patient's trial eligibility updates in milliseconds.", C.accent2);

// ==========================================
// SLIDE 13: THE LIVE DEMO WORKFLOW
// ==========================================
let slide13 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide13, "Our Prototype Demo", "What we built for the hackathon.");
slide13.addShape(pptx.ShapeType.rect, { x: 1.0, y: 1.6, w: 8.5, h: 0.4, fill: { color: C.cardBg } });
slide13.addText("Live Full-Stack Application: React SPA + FastAPI Backend + SQLite", { x: 1.0, y: 1.6, w: 8.5, h: 0.4, color: C.accent1, bold: true, align: "center" });

addCard(slide13, 1.0, 2.2, 2.6, 2.6, "Step 1: Selection", "Pull a live clinical trial from our scraped database.", C.textMuted);
addCard(slide13, 4.0, 2.2, 2.6, 2.6, "Step 2: Engine", "View the PyVis Graph. Run the AST Math. Generate RAG.", C.accent2);
addCard(slide13, 7.0, 2.2, 2.6, 2.6, "Step 3: Simulate", "Inject a live Lab Result and watch the eligibility flip.", C.accent1);

// ==========================================
// SLIDE 14: ENTERPRISE VALUE
// ==========================================
let slide14 = pptx.addSlide({ masterName: "DARK_CONTENT" });
addTitle(slide14, "Business Value & Scale", "Why Hexaware and clients need this.");
addCard(slide14, 1.0, 1.8, 4.0, 1.5, "90% Faster Screening", "Automated AST execution drops chart review from hours to milliseconds.", C.accent2);
addCard(slide14, 5.5, 1.8, 4.0, 1.5, "Zero AI Liability", "Because the final decision is math, not an LLM, hospitals avoid medical malpractice risks.", C.accent2);
addCard(slide14, 1.0, 3.5, 4.0, 1.5, "Out-of-the-Box Compliance", "Local Presidio scrubbing means immediate HIPAA and GDPR readiness.", C.accent1);
addCard(slide14, 5.5, 3.5, 4.0, 1.5, "Agnostic Integration", "Graph logic can ingest FHIR, HL7, and proprietary EHR data lakes cleanly.", C.accent1);

// ==========================================
// SLIDE 15: CONCLUSION
// ==========================================
let slide15 = pptx.addSlide({ masterName: "DARK_TITLE" });
slide15.addShape(pptx.ShapeType.rect, { x: 0, y: '35%', w: '100%', h: '30%', fill: { color: "0B1120" } });
slide15.addText("THANK YOU / Q&A", { x: 0, y: '36%', w: '100%', h: 1.5, fontSize: 72, fontFace: "Helvetica Neue", bold: true, color: C.accent2, align: "center", letterSpacing: 0.1 });
slide15.addText("TEAM VISIONARIES | Hexaware Mavericks Hackathon 2026", { x: 0, y: '52%', w: '100%', h: 0.6, fontSize: 20, fontFace: "Helvetica Neue", color: C.textMuted, align: "center" });
slide15.addImage({ x: 3.5, y: 4.2, w: 3, h: 1.0, path: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=500&q=80", sizing: { type: "crop" } });

// Save
pptx.writeFile({ fileName: "Visionaries_Hackathon_Pitch_15_Slides.pptx" }).then(fileName => {
    console.log(`Created presentation: ${fileName}`);
});
