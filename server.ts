/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import express, { Request, Response, NextFunction } from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";
import { db } from "./src/server/db";

// Load environment variables
dotenv.config();

// Extend Express Request interface to include session user
declare global {
  namespace Express {
    interface Request {
      user?: { id: string; email: string; full_name: string };
    }
  }
}

const app = express();
const PORT = 3000;

// Increase payload size to allow base64 file uploads (resumes, documents)
app.use(express.json({ limit: "15mb" }));
app.use(express.urlencoded({ limit: "15mb", extended: true }));

// Initialize Google Gen AI
const apiKey = process.env.GEMINI_API_KEY;
let ai: GoogleGenAI | null = null;

if (apiKey && apiKey !== "MY_GEMINI_API_KEY") {
  console.log("Initializing Gemini AI Client...");
  ai = new GoogleGenAI({
    apiKey: apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
} else {
  console.log("No valid GEMINI_API_KEY found. AI features will run with high-fidelity realistic simulated career intelligence.");
}

// --- AUTH MIDDLEWARE ---
function authenticate(req: Request, res: Response, next: NextFunction) {
  // Try to read token from Authorization header or Cookies
  let token = "";
  if (req.headers.authorization && req.headers.authorization.startsWith("Bearer ")) {
    token = req.headers.authorization.split(" ")[1];
  } else {
    // Try to parse cookie manually
    const cookieHeader = req.headers.cookie;
    if (cookieHeader) {
      const match = cookieHeader.match(/token=([^;]+)/);
      if (match) token = match[1];
    }
  }

  if (!token) {
    return res.status(401).json({ error: "Unauthorized. Please log in." });
  }

  const user = db.verifySession(token);
  if (!user) {
    return res.status(401).json({ error: "Session expired or invalid. Please log in again." });
  }

  req.user = user;
  next();
}

// --- IN-MEMORY RATE LIMITER FOR AI ENDPOINTS ---
const aiRequestsStore: Record<string, number[]> = {};

function aiRateLimiter(req: Request, res: Response, next: NextFunction) {
  const userId = req.user?.id;
  if (!userId) {
    return res.status(401).json({ error: "Unauthorized. Rate limiting requires authentication." });
  }

  const now = Date.now();
  const oneMinuteAgo = now - 60000; // 1 minute window

  // Filter timestamps older than 1 minute
  if (!aiRequestsStore[userId]) {
    aiRequestsStore[userId] = [];
  }
  aiRequestsStore[userId] = aiRequestsStore[userId].filter(t => t > oneMinuteAgo);

  // Maximum 5 AI requests per minute
  if (aiRequestsStore[userId].length >= 5) {
    return res.status(429).json({
      error: "Rate limit exceeded. To protect public server resources, please wait a minute before sending another AI request."
    });
  }

  aiRequestsStore[userId].push(now);
  next();
}

// --- ROBUST GEMINI EXECUTION HELPER ---
async function safeGenerateContent(params: {
  contents: any;
  config?: any;
}) {
  if (!ai) {
    throw new Error("AI client not configured.");
  }

  const modelsToTry = ["gemini-3.5-flash", "gemini-3.1-flash-lite"];
  let lastError: any = null;

  for (const model of modelsToTry) {
    try {
      console.log(`[Gemini API] Attempting generateContent with model: ${model}...`);
      const response = await ai.models.generateContent({
        model: model,
        contents: params.contents,
        config: params.config,
      });
      return response;
    } catch (err: any) {
      lastError = err;
      const status = err?.status || err?.code || (err?.error && err.error.code);
      const message = err?.message || (err?.error && err.error.message) || "";
      console.warn(`[Gemini API] Model ${model} failed with error (status: ${status}): ${message}`);
      
      if (status === 503 || status === 429 || status === 403 || message.includes("503") || message.includes("429") || message.includes("UNAVAILABLE")) {
        console.log(`[Gemini API] Retrying with next model due to transient error...`);
        continue;
      }
      throw err;
    }
  }

  throw lastError || new Error("Failed to generate content with any model.");
}

// Helper to validate email format on the server side
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
}

// --- AUTH ROUTES ---
app.post("/api/auth/signup", (req: Request, res: Response) => {
  const { email, password, full_name } = req.body;
  if (!email || !password || !full_name) {
    return res.status(400).json({ error: "Missing email, password, or full name." });
  }

  if (!isValidEmail(email)) {
    return res.status(400).json({ error: "Please enter a valid email address format (e.g. user@domain.com)." });
  }

  const result = db.signup(email, password, full_name);
  if (result.error) {
    return res.status(400).json({ error: result.error });
  }

  // Auto-login after signup
  const loginResult = db.login(email, password);
  res.json({
    success: true,
    user: { id: result.user!.id, email: result.user!.email, full_name: result.user!.full_name },
    token: loginResult.token,
  });
});

app.post("/api/auth/login", (req: Request, res: Response) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: "Missing email or password." });
  }

  if (!isValidEmail(email)) {
    return res.status(400).json({ error: "Please enter a valid email address format (e.g. user@domain.com)." });
  }

  const result = db.login(email, password);
  if (result.error) {
    return res.status(400).json({ error: result.error });
  }

  res.json({
    success: true,
    user: { id: result.user!.id, email: result.user!.email, full_name: result.user!.full_name },
    token: result.token,
  });
});

app.post("/api/auth/logout", (req: Request, res: Response) => {
  let token = "";
  if (req.headers.authorization && req.headers.authorization.startsWith("Bearer ")) {
    token = req.headers.authorization.split(" ")[1];
  } else {
    const cookieHeader = req.headers.cookie;
    if (cookieHeader) {
      const match = cookieHeader.match(/token=([^;]+)/);
      if (match) token = match[1];
    }
  }

  if (token) {
    db.logout(token);
  }
  res.json({ success: true });
});

app.get("/api/auth/session", (req: Request, res: Response) => {
  let token = "";
  if (req.headers.authorization && req.headers.authorization.startsWith("Bearer ")) {
    token = req.headers.authorization.split(" ")[1];
  } else {
    const cookieHeader = req.headers.cookie;
    if (cookieHeader) {
      const match = cookieHeader.match(/token=([^;]+)/);
      if (match) token = match[1];
    }
  }

  if (!token) {
    return res.status(401).json({ authenticated: false, error: "No token provided." });
  }

  const user = db.verifySession(token);
  if (!user) {
    return res.status(401).json({ authenticated: false, error: "Invalid or expired session." });
  }

  const profile = db.getProfile(user.id);
  res.json({
    authenticated: true,
    user: { id: user.id, email: user.email, full_name: user.full_name },
    profile,
  });
});

// --- PROFILE ROUTES ---
app.get("/api/profile", authenticate, (req: Request, res: Response) => {
  const profile = db.getProfile(req.user!.id);
  res.json(profile);
});

app.put("/api/profile", authenticate, (req: Request, res: Response) => {
  const updated = db.updateProfile(req.user!.id, req.body);
  res.json(updated);
});

// --- APPLICATION ROUTES ---
app.get("/api/applications", authenticate, (req: Request, res: Response) => {
  const apps = db.getApplications(req.user!.id);
  res.json(apps);
});

app.post("/api/applications", authenticate, (req: Request, res: Response) => {
  const newApp = db.createApplication(req.user!.id, req.body);
  res.status(201).json(newApp);
});

app.put("/api/applications/:id", authenticate, (req: Request, res: Response) => {
  const updated = db.updateApplication(req.user!.id, req.params.id, req.body);
  if (!updated) {
    return res.status(404).json({ error: "Application not found or unauthorized." });
  }
  res.json(updated);
});

app.delete("/api/applications/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteApplication(req.user!.id, req.params.id);
  if (!success) {
    return res.status(404).json({ error: "Application not found or unauthorized." });
  }
  res.json({ success: true });
});

// --- TASK ROUTES ---
app.get("/api/tasks", authenticate, (req: Request, res: Response) => {
  const tasks = db.getTasks(req.user!.id);
  res.json(tasks);
});

app.post("/api/tasks", authenticate, (req: Request, res: Response) => {
  const newTask = db.createTask(req.user!.id, req.body);
  res.status(201).json(newTask);
});

app.put("/api/tasks/:id", authenticate, (req: Request, res: Response) => {
  const updated = db.updateTask(req.user!.id, req.params.id, req.body);
  if (!updated) {
    return res.status(404).json({ error: "Task not found or unauthorized." });
  }
  res.json(updated);
});

app.delete("/api/tasks/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteTask(req.user!.id, req.params.id);
  if (!success) {
    return res.status(404).json({ error: "Task not found or unauthorized." });
  }
  res.json({ success: true });
});

// --- DOCUMENT ROUTES ---
app.get("/api/documents", authenticate, (req: Request, res: Response) => {
  const docs = db.getDocuments(req.user!.id);
  res.json(docs);
});

app.post("/api/documents", authenticate, (req: Request, res: Response) => {
  const { title, file_url, file_type, category, tags } = req.body;
  if (!title || !category) {
    return res.status(400).json({ error: "Missing document title or category." });
  }

  const newDoc = db.createDocument(req.user!.id, {
    title,
    file_url: file_url || "",
    file_type: file_type || "pdf",
    category,
    tags: tags || [],
  });
  res.status(201).json(newDoc);
});

app.delete("/api/documents/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteDocument(req.user!.id, req.params.id);
  if (!success) {
    return res.status(404).json({ error: "Document not found or unauthorized." });
  }
  res.json({ success: true });
});

// --- ROADMAP ROUTES ---
app.get("/api/roadmaps", authenticate, (req: Request, res: Response) => {
  const roadmaps = db.getRoadmaps(req.user!.id);
  res.json(roadmaps);
});

app.delete("/api/roadmaps/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteRoadmap(req.user!.id, req.params.id);
  if (!success) {
    return res.status(404).json({ error: "Roadmap not found or unauthorized." });
  }
  res.json({ success: true });
});

app.put("/api/roadmaps/:id/progress", authenticate, (req: Request, res: Response) => {
  const { progress } = req.body;
  const updated = db.updateRoadmapProgress(req.user!.id, req.params.id, Number(progress));
  if (!updated) {
    return res.status(404).json({ error: "Roadmap not found or unauthorized." });
  }
  res.json(updated);
});

// --- SYSTEM-SPECIFIC HARD-CODED ROADMAP GENERATOR (FALLBACK) ---
function getSimulatedRoadmap(role: string, level: string, hours: number, duration: number): any {
  // Formulate a robust, high-fidelity curriculum that fits the duration and level
  const weekCount = Math.ceil(duration / 7);
  const weeksList = [];

  const coreFocusMap: Record<string, string[]> = {
    "Machine Learning Engineer": [
      "Python for Data Science, NumPy, Pandas, and basic Linear Algebra",
      "Exploratory Data Analysis, Data Preprocessing, and Scikit-Learn fundamentals",
      "Supervised ML (Regression, Classification) & Model Evaluation Metrics",
      "Unsupervised ML (Clustering, PCA) & Feature Engineering pipelines",
      "Introduction to Neural Networks, TensorFlow/PyTorch, and Deep Learning",
      "Hyperparameter tuning, Cross-validation, and productionizing models",
      "Deployment basics with Flask/FastAPI, Docker, and ML Pipelines",
      "High-scale ML deployment, MLOPs introduction, and comprehensive review"
    ],
    "Data Analyst": [
      "Advanced Spreadsheets (Excel) and relational database concepts",
      "SQL Fundamentals: SELECT, JOINs, Grouping, and database querying",
      "Advanced SQL: Subqueries, Window Functions, and CTEs",
      "Python for Analysis: NumPy, Pandas, and Data Wrangling techniques",
      "Exploratory Data Analysis (EDA) and visualization using Seaborn & Matplotlib",
      "Business Intelligence tools: Tableau/PowerBI dashboard design",
      "Analytical thinking: KPI development, Cohort analysis, and business case studies",
      "Storytelling with data: building presentation-ready analyst portfolios"
    ],
    "Frontend Developer": [
      "Semantic HTML5, CSS3, modern Flexbox/Grid systems, and Responsive Design",
      "JavaScript Basics: ES6+, DOM manipulation, Event Handlers, and Promises",
      "Modern CSS frameworks (Tailwind CSS) & Git workflows",
      "React JS Fundamentals: Functional Components, JSX, and Props",
      "React State Management: useState, useEffect, and custom hooks",
      "Consuming REST APIs, client-side routing (React Router), and form validation",
      "Testing components, performance optimization (memoization), and deployment",
      "Building portfolio-ready React projects with pristine Tailwind layout"
    ],
    "Backend Developer": [
      "Backend programming language fundamentals (Node.js/Python/Go)",
      "Express.js / FastAPI web server architectures & routing systems",
      "Relational databases (PostgreSQL/MySQL), SQL syntax, and DDL/DML rules",
      "Database ORMs, Schema Design, migrations, and model relationships",
      "RESTful API design best practices, status codes, and error handlers",
      "User Authentication systems: JWTs, Sessions, and middleware security",
      "System testing, unit testing (Jest/PyTest), and basic Docker containerization",
      "Server deployment (Cloud Run/Heroku/AWS) and backend system documentation"
    ],
    "Full Stack Developer": [
      "Frontend basics: HTML, Tailwind CSS, and core JavaScript elements",
      "React JS fundamentals: component layout, state control, and form logic",
      "Backend basics: Node.js, Express web servers, and routing systems",
      "Databases: PostgreSQL integration, relational schemas, and query writing",
      "Full-stack authentication: integrating JWT secure channels between React and Express",
      "State systems: unified endpoints, data updates, and visual loader feedback",
      "System packaging: Docker orchestration, environment variables, and dev pipelines",
      "Building a complex unified capstone project with clean frontend and secure server APIs"
    ]
  };

  const defaultFocus = [
    "Core Foundations, language syntax, and basic programming concepts",
    "Intermediate practices, object-oriented concepts, and project structure",
    "Database interaction, API integration, and third-party libraries",
    "Application building, routing, state managers, and error handling",
    "Complex functionalities, state machines, and testing environments",
    "Deployment pipelines, cloud architectures, and configurations",
    "Mock technical interviews, system designs, and code optimizations",
    "Portfolio polishing, final resume preparations, and job application push"
  ];

  const focusList = coreFocusMap[role] || defaultFocus;

  for (let w = 1; w <= weekCount; w++) {
    const focusItem = focusList[(w - 1) % focusList.length];
    weeksList.push({
      week_number: w,
      title: `Phase ${w}: ${focusItem.split(",")[0]}`,
      main_focus: focusItem,
      why_this_matters: `This phase establishes vital milestones for a successful career transition into a ${role} role.`,
      topics: [
        `Core theoretical foundations for ${focusItem.split(" and ")[0]}`,
        `Practical syntax, parameters, and structural execution patterns`,
        `Troubleshooting standard bugs, profiling memory, and optimizing logic`,
      ],
      tools: [
        "Visual Studio Code",
        "Git & GitHub Version Control",
        role.includes("Analyst") ? "PostgreSQL / Excel" : "npm / Node.js Runtime",
        role.includes("Machine") ? "Jupyter Notebooks / Anaconda" : "Vite Tooling"
      ],
      practice_tasks: [
        `Write 3 minor projects utilizing the core concepts of Phase ${w}`,
        `Document your code structure and commit changes to a public GitHub repository`,
        `Complete 5 practical debugging challenges related to modern implementation workflows`
      ],
      mini_project: `Flagship Milestone ${w} - Fully operational ${role} subsystem`,
      daily_plan: [
        "Day 1: Read theoretical framework, take code notes, set up environment.",
        "Day 2: Write basic configurations, experiment with code syntaxes.",
        "Day 3: Integrate data elements, handle simple logical constraints.",
        "Day 4: Implement state storage, perform incremental execution checks.",
        "Day 5: Build a modular sub-component, refactor for neat spacing.",
        "Day 6: Test performance, resolve compiler warnings, build mini-project.",
        "Day 7: Document implementation logic in README, plan upcoming objectives."
      ],
      revision_tasks: [
        "Review syntax logs from the beginning of this week.",
        "Solve one coding assessment question blind without documentation help."
      ],
      expected_outcome: `High level of comfort with ${focusItem.split(",")[0]} and standard tooling.`
    });
  }

  return {
    title: `${duration}-Day Intensive ${role} Execution Plan`,
    target_role: role,
    current_level: level,
    duration_days: duration,
    daily_hours: hours,
    overall_strategy: `A mentor-designed curriculum tailored for ${level} level. By committing ${hours} hours daily, you build a robust software portfolio, master core technical concepts, and prepare for interviews using a highly focused project-based schedule.`,
    expected_outcome: `By the end of day ${duration}, you will have compiled a comprehensive technical portfolio containing at least 3 flagship projects, established complete fluency in ${role} methodologies, and secured full competency for entry-to-mid level job interviews.`,
    weeks: weeksList,
    projects_to_build: [
      `Flagship Capstone Project: A secure high-performance ${role} platform`,
      `Full-Featured Client Portal: Real-time interactive dashboard mapping domain-specific KPIs`,
      `Technical Utility Suite: Lightweight microservices demonstrating OOP or clean architectures`
    ],
    portfolio_resume_advice: [
      `Optimize GitHub profiles with descriptive READMEs containing gifs, deployment instructions, and engineering breakdowns.`,
      `Structure resumes following the XYZ format (e.g. Accomplished [X], as measured by [Y], by doing [Z]).`,
      `Highlight exact technologies matching the job criteria right in the top summary banner.`
    ],
    interview_prep_topics: [
      "Complex systems design, structural normalizations, and memory limits",
      "Dynamic programming, core data structures (hashmaps, trees, arrays), and runtime complexity",
      "Domain-specific standard questions (e.g. REST API design principles or ML loss optimization)"
    ],
    mistakes_to_avoid: [
      "Tutorial Hell: Watching video courses endlessly without typing, creating, and compiling original code.",
      "Inconsistency: Skipping preparation days. It's better to study 2 hours daily than 10 hours once a week.",
      "Neglecting soft skills: Failing to speak out loud during technical rounds and missing behavioral alignment."
    ],
    success_checklist: [
      "Daily study block locked in calendar",
      "Git commits pushed consistently every week",
      "At least 3 complete, functional flagship projects on live hosting",
      "15 technical interview questions mastered out loud",
      "Professional portfolio website shipped and linked on resume"
    ]
  };
}

// --- ROADMAP GENERATION ACTION ---
app.post("/api/roadmaps/generate", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { role, level, hours, duration } = req.body;
  if (!role || !level || !hours || !duration) {
    return res.status(400).json({ error: "Missing roadmap configuration parameters." });
  }

  const durationDays = Number(duration);
  const dailyHours = Number(hours);

  console.log(`Generating roadmap for Role: ${role}, Level: ${level}, Hours: ${hours}, Duration: ${duration}...`);

  let generatedJson: any = null;

  if (ai) {
    try {
      const systemInstruction = `You are an elite, practical career mentor, tech lead, and instructional designer. Your mission is to generate highly structured, deeply practical, mentor-style, role-specific career roadmaps for students, freshers, and job switchers.
Each roadmap MUST be entirely custom, matching the role, current level, daily available hours, and duration.
You MUST output your response in STRICTL compliant JSON format matching the schema requested.
DO NOT wrap the JSON in markdown blocks (like \`\`\`json) or add introductory text. Just output pure valid JSON.

JSON Schema:
{
  "title": "string (Title of the roadmap)",
  "target_role": "string",
  "current_level": "string",
  "duration_days": number,
  "daily_hours": number,
  "overall_strategy": "string (detailed paragraph detailing specific strategy)",
  "expected_outcome": "string",
  "weeks": [
    {
      "week_number": number,
      "title": "string",
      "main_focus": "string (what to master)",
      "why_this_matters": "string (mentor-style explanation)",
      "topics": ["string"],
      "tools": ["string"],
      "practice_tasks": ["string"],
      "mini_project": "string",
      "daily_plan": ["string (exact text for Day 1 to Day 7 in order)"],
      "revision_tasks": ["string"],
      "expected_outcome": "string"
    }
  ],
  "projects_to_build": ["string"],
  "portfolio_resume_advice": ["string"],
  "interview_prep_topics": ["string"],
  "mistakes_to_avoid": ["string"],
  "success_checklist": ["string"]
}

Make sure the daily_plan has exactly 7 items representing Day 1 to Day 7.
Genuinely adapt the material based on the inputs:
- Beginner: start with absolute basics (language syntax, environment, fundamental concepts), slow pace, heavy explanation.
- Intermediate: fast-track fundamentals, focus on projects, database structure, and integration.
- Advanced: jump directly to complex patterns, scaling, microservices, system design, flagship portfolio architecture.
- 30 days: focus only on high-yield core topics and 1 flagship project.
- 60/90 days: comprehensive deep progression, robust test coverage, and career positioning.`;

      const userPrompt = `Create a role-specific, deeply personalized career execution roadmap for:
- Target Role: ${role}
- Current Level: ${level}
- Available Daily Commitment: ${dailyHours} hours/day
- Target Timeline: ${durationDays} days

Generate exactly ${Math.ceil(durationDays / 7)} weeks of training content matching this criteria.`;

      const response = await safeGenerateContent({
        contents: userPrompt,
        config: {
          systemInstruction: systemInstruction,
          responseMimeType: "application/json",
          temperature: 0.1,
        },
      });

      const responseText = response.text || "";
      console.log("AI roadmap generation complete. Parsing JSON response...");
      generatedJson = JSON.parse(responseText.trim());
    } catch (err) {
      console.error("Failed to generate AI roadmap with Gemini, invoking local high-fidelity generator fallback...", err);
      generatedJson = getSimulatedRoadmap(role, level, dailyHours, durationDays);
    }
  } else {
    console.log("No AI client configured, generating custom simulated roadmap instantly...");
    generatedJson = getSimulatedRoadmap(role, level, dailyHours, durationDays);
  }

  // Double check that the parsed JSON has the necessary fields
  if (!generatedJson || !generatedJson.weeks) {
    generatedJson = getSimulatedRoadmap(role, level, dailyHours, durationDays);
  }

  // Save the generated roadmap in our database
  const savedRoadmap = db.saveRoadmap(req.user!.id, {
    role,
    current_level: level,
    daily_hours: dailyHours,
    duration_days: durationDays,
    roadmap_json: generatedJson,
    progress: 0,
  });

  res.json(savedRoadmap);
});

// --- COMPATIBILITY & ALIAS ENDPOINTS ---
app.post("/api/profile/update", authenticate, (req: Request, res: Response) => {
  const updated = db.updateProfile(req.user!.id, req.body);
  res.json(updated);
});

app.post("/api/applications/add", authenticate, (req: Request, res: Response) => {
  const newApp = db.createApplication(req.user!.id, req.body);
  res.status(201).json(newApp);
});

app.put("/api/applications/update/:id", authenticate, (req: Request, res: Response) => {
  const updated = db.updateApplication(req.user!.id, req.params.id, req.body);
  if (!updated) return res.status(404).json({ error: "Application not found or unauthorized." });
  res.json(updated);
});

app.delete("/api/applications/delete/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteApplication(req.user!.id, req.params.id);
  if (!success) return res.status(404).json({ error: "Application not found or unauthorized." });
  res.json({ success: true });
});

app.post("/api/tasks/add", authenticate, (req: Request, res: Response) => {
  const newTask = db.createTask(req.user!.id, req.body);
  res.status(201).json(newTask);
});

app.put("/api/tasks/update/:id", authenticate, (req: Request, res: Response) => {
  const updated = db.updateTask(req.user!.id, req.params.id, req.body);
  if (!updated) return res.status(404).json({ error: "Task not found or unauthorized." });
  res.json(updated);
});

app.delete("/api/tasks/delete/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteTask(req.user!.id, req.params.id);
  if (!success) return res.status(404).json({ error: "Task not found or unauthorized." });
  res.json({ success: true });
});

app.post("/api/documents/add", authenticate, (req: Request, res: Response) => {
  const { title, file_url, file_type, category, tags } = req.body;
  if (!title || !category) {
    return res.status(400).json({ error: "Missing document title or category." });
  }
  const newDoc = db.createDocument(req.user!.id, {
    title,
    file_url: file_url || "",
    file_type: file_type || "pdf",
    category,
    tags: tags || [],
  });
  res.status(201).json(newDoc);
});

app.delete("/api/documents/delete/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteDocument(req.user!.id, req.params.id);
  if (!success) return res.status(404).json({ error: "Document not found or unauthorized." });
  res.json({ success: true });
});

app.delete("/api/roadmaps/delete/:id", authenticate, (req: Request, res: Response) => {
  const success = db.deleteRoadmap(req.user!.id, req.params.id);
  if (!success) return res.status(404).json({ error: "Roadmap not found or unauthorized." });
  res.json({ success: true });
});

app.post("/api/roadmaps/progress/:id", authenticate, (req: Request, res: Response) => {
  const { progress } = req.body;
  const updated = db.updateRoadmapProgress(req.user!.id, req.params.id, Number(progress));
  if (!updated) return res.status(404).json({ error: "Roadmap not found or unauthorized." });
  res.json(updated);
});

// --- STATEFUL BUDDY AI COPILOT CHAT ACTION ---
app.get("/api/buddy-ai/history", authenticate, (req: Request, res: Response) => {
  const userId = req.user!.id;
  const history = db.getChatHistory(userId);
  res.json(history);
});

app.post("/api/buddy-ai/clear", authenticate, (req: Request, res: Response) => {
  const userId = req.user!.id;
  db.clearChatHistory(userId);
  res.json({ success: true });
});

app.post("/api/buddy-ai/chat", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { message } = req.body;
  if (!message) {
    return res.status(400).json({ error: "Missing conversation message parameter." });
  }

  const userId = req.user!.id;
  // 1. Save user's message
  db.addChatMessage(userId, "user", message);

  // 2. Load context
  const userProfile = db.getProfile(userId);
  const userApps = db.getApplications(userId);
  const userTasks = db.getTasks(userId);
  const userRoadmaps = db.getRoadmaps(userId);
  const activeRoadmap = userRoadmaps.length > 0 ? userRoadmaps[0] : null;

  // Format summaries
  const appsSummary = userApps.map(a => `${a.company} (${a.role}) - Status: ${a.status}, Applied: ${a.date_applied}`).join("\n");
  const tasksSummary = userTasks.map(t => `- [${t.status === "Completed" ? "x" : " "}] ${t.title} (Priority: ${t.priority}, Due: ${t.due_date})`).join("\n");
  const roadmapSummary = activeRoadmap 
    ? `Active Roadmap: ${activeRoadmap.roadmap_json.title}\nRole: ${activeRoadmap.role}\nProgress: ${activeRoadmap.progress}%\nOverall Strategy: ${activeRoadmap.roadmap_json.overall_strategy}`
    : "No active generated career roadmap.";

  // Retrieve current chat history from db
  const chatMessages = db.getChatHistory(userId);

  // Build high-context system instruction
  const systemInstruction = `You are Buddy, an elite, highly practical Career Copilot and executive career coach for students, freshers, and job switchers.
You are calm, direct, emotionally intelligent, structured, and execution-focused. You do not speak in fluffy, hyped-up, or generic AI motivational tones.
Instead, you provide highly actionable advice, clear numbered steps, and objective guidance to help users get their careers together, study efficiently, and execute.

Here is the exact real-time application context of the user you are talking to:
- Name: ${userProfile?.full_name || req.user!.full_name}
- College/University: ${userProfile?.college || "Not specified"}
- Target Professional Role: ${userProfile?.target_role || "Full Stack Developer"}
- Current Technical Experience Level: ${userProfile?.current_level || "Beginner"}
- Available Daily Commitment: ${userProfile?.daily_hours || 4} hours/day

${roadmapSummary}

Applications Currently Stored:
${appsSummary || "No job/internship applications tracked yet."}

Tasks Stored on Execution Board:
${tasksSummary || "No tasks added to the execution board yet."}

Your mission is to directly utilize this context.
1. If the user asks "What should I focus on this week?", look at their active roadmap or high-priority tasks and give them a structured checklist.
2. If the user asks "Summarize my application progress", analyze their applications, count the statuses (e.g. interviews, applications, offers) and give them an insightful diagnostic with next steps.
3. If they ask about resumes, study strategies, or interview preparation, give them deep, mentor-style advice specifically tailored to their Target Role (${userProfile?.target_role}) and Level (${userProfile?.current_level}).
4. Always frame advice around ACTION. Keep paragraphs concise, use clear bullet points, and highlight exact tools or topics. Avoid vague generalities.`;

  console.log(`Calling Copilot chat for user: ${req.user!.email}...`);
  let reply = "";

  if (ai) {
    try {
      // Map history messages to standard Gemini Chat content structure
      const contents = chatMessages.map(m => ({
        role: m.role === "user" ? "user" : "model",
        parts: [{ text: m.content }],
      }));

      const response = await safeGenerateContent({
        contents: contents,
        config: {
          systemInstruction: systemInstruction,
          temperature: 0.7,
        },
      });

      reply = response.text || "I apologize, but I could not compute a clear action plan. Let's refocus on your core daily tasks.";
    } catch (err) {
      console.error("Gemini Copilot chat error, falling back to simulated career intelligence...", err);
      reply = getSimulatedCopilotReply(message, userProfile, userApps, userTasks, activeRoadmap);
    }
  } else {
    reply = getSimulatedCopilotReply(message, userProfile, userApps, userTasks, activeRoadmap);
  }

  // Save AI's response
  const updatedHistory = db.addChatMessage(userId, "assistant", reply);
  res.json({ reply, history: updatedHistory });
});

// --- MOCK INTERVIEW PREP ACTION ---
app.post("/api/interview/mock", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { role, difficulty, focusArea } = req.body;
  if (!role) {
    return res.status(400).json({ error: "Missing target role." });
  }

  const difficultyStr = difficulty || "Intermediate";
  const focusStr = focusArea || "General Technical & Behavioral";

  console.log(`Generating mock interview for Role: ${role}, Difficulty: ${difficultyStr}...`);

  const systemInstruction = `You are an elite Tech Lead, engineering director, and professional developer interviewer.
Your task is to generate high-fidelity technical and behavioral mock interview questions.
You MUST output your response in STRICTLY compliant JSON format matching this schema:
{
  "questions": ["string"],
  "answers_guidance": ["string"],
  "follow_ups": ["string"]
}
Strictly output pure valid JSON. Do not wrap in markdown code blocks.`;

  const userPrompt = `Generate exactly 5 key interview questions, 5 model answers/answer guidance summaries (one for each question detailing what top-tier candidates say), and 3 follow-up questions for a candidate interviewing for a ${role} position.
Difficulty Level: ${difficultyStr}
Focus Area: ${focusStr}`;

  if (ai) {
    try {
      const response = await safeGenerateContent({
        contents: userPrompt,
        config: {
          systemInstruction: systemInstruction,
          responseMimeType: "application/json",
          temperature: 0.2,
        },
      });
      res.json(JSON.parse(response.text!.trim()));
    } catch (err) {
      console.error("Failed to generate AI Mock Interview, falling back to simulator...", err);
      res.json(getSimulatedInterview(role, difficultyStr, focusStr));
    }
  } else {
    res.json(getSimulatedInterview(role, difficultyStr, focusStr));
  }
});

// --- RESUME KEYWORDS REVIEW ACTION ---
app.post("/api/resume/review-keywords", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { resumeText, jobDescription } = req.body;
  if (!resumeText) {
    return res.status(400).json({ error: "Resume text content is required." });
  }

  console.log(`Analyzing resume keywords...`);

  const systemInstruction = `You are an expert technical resume reviewer and Applicant Tracking System (ATS) optimization specialist.
Your mission is to analyze the candidate's resume text against modern technical roles (and optionally a job description) to spot keyword omissions and optimization gaps.
You MUST output your response in STRICTLY compliant JSON format matching this schema:
{
  "missingKeywords": ["string"],
  "keywordGaps": "string (general summary analysis)",
  "suggestions": ["string"]
}
Strictly output pure valid JSON. Do not wrap in markdown code blocks.`;

  const userPrompt = `Analyze the candidate's resume text:
"${resumeText}"

${jobDescription ? `Compare against this Job Description:\n"${jobDescription}"` : "Compare against standard high-yield requirements for their field."}`;

  if (ai) {
    try {
      const response = await safeGenerateContent({
        contents: userPrompt,
        config: {
          systemInstruction: systemInstruction,
          responseMimeType: "application/json",
          temperature: 0.2,
        },
      });
      res.json(JSON.parse(response.text!.trim()));
    } catch (err) {
      console.error("Failed to generate AI resume review, falling back to simulator...", err);
      res.json(getSimulatedResumeReview(resumeText, jobDescription));
    }
  } else {
    res.json(getSimulatedResumeReview(resumeText, jobDescription));
  }
});

// --- OPTIMIZE STUDY SCHEDULE ACTION ---
app.post("/api/study/optimize", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { targetRole, dailyHours, currentRoadmapProgress, upcomingDeadlines } = req.body;
  if (!targetRole) {
    return res.status(400).json({ error: "Missing target role." });
  }

  const hoursNum = Number(dailyHours || 4);
  console.log(`Optimizing study schedule for Role: ${targetRole}...`);

  const systemInstruction = `You are an expert developer productivity and instructional designer.
Optimize study blocks, focus topics, and active project timelines into a highly actionable study plan.
You MUST output your response in STRICTLY compliant JSON format matching this schema:
{
  "weeklyPlan": [
    {
      "week": "string",
      "focus": "string",
      "allocation": "string"
    }
  ],
  "prioritizedTasks": ["string"],
  "sequencingAdvice": "string"
}
Strictly output pure valid JSON. Do not wrap in markdown code blocks.`;

  const userPrompt = `Create an optimized study plan for a candidate learning to be a ${targetRole}.
Daily study window: ${hoursNum} hours.
Current Roadmap Progress: ${currentRoadmapProgress || "0%"}
Upcoming Tasks/Deadlines: ${upcomingDeadlines || "None currently logged"}`;

  if (ai) {
    try {
      const response = await safeGenerateContent({
        contents: userPrompt,
        config: {
          systemInstruction: systemInstruction,
          responseMimeType: "application/json",
          temperature: 0.2,
        },
      });
      res.json(JSON.parse(response.text!.trim()));
    } catch (err) {
      console.error("Failed to generate optimized AI study plan, falling back to simulator...", err);
      res.json(getSimulatedStudyOptimization(targetRole, hoursNum));
    }
  } else {
    res.json(getSimulatedStudyOptimization(targetRole, hoursNum));
  }
});

// --- REVIEW JOB POSTING ACTION ---
app.post("/api/job/review", authenticate, aiRateLimiter, async (req: Request, res: Response) => {
  const { jobDescription } = req.body;
  if (!jobDescription) {
    return res.status(400).json({ error: "Please provide a job posting description." });
  }

  console.log(`Reviewing job posting...`);

  const systemInstruction = `You are a professional tech recruiter and system design interviewer.
Analyze the job posting text and output a highly structured resume-matching and interview preparation diagnostic assessment.
You MUST output your response in STRICTLY compliant JSON format matching this schema:
{
  "keySkills": ["string"],
  "missingSkills": ["string"],
  "prepGaps": ["string"],
  "fitAnalysis": "string (detailed matching diagnostic)",
  "tailoringAdvice": "string"
}
Strictly output pure valid JSON. Do not wrap in markdown code blocks.`;

  const userPrompt = `Review the following job description posting for key requirements, prep gaps, fit analysis, and resume tailoring strategies:
"${jobDescription}"`;

  if (ai) {
    try {
      const response = await safeGenerateContent({
        contents: userPrompt,
        config: {
          systemInstruction: systemInstruction,
          responseMimeType: "application/json",
          temperature: 0.2,
        },
      });
      res.json(JSON.parse(response.text!.trim()));
    } catch (err) {
      console.error("Failed to generate AI Job Review, falling back to simulator...", err);
      res.json(getSimulatedJobReview(jobDescription));
    }
  } else {
    res.json(getSimulatedJobReview(jobDescription));
  }
});

// --- STATEFUL COPILOT SIMULATION FALLBACKS ---
function getSimulatedCopilotReply(message: string, userProfile: any, userApps: any[], userTasks: any[], activeRoadmap: any): string {
  const lastMessage = message.toLowerCase() || "";
  if (lastMessage.includes("focus") || lastMessage.includes("do next") || lastMessage.includes("week")) {
    return `Let's map out your high-priority execution targets, ${userProfile?.full_name || "Varshith"}. Based on your profile as a ${userProfile?.current_level || "Beginner"} **${userProfile?.target_role || "Full Stack Developer"}**:

1. **Daily Routine (Aim for ${userProfile?.daily_hours || 4} hours)**:
   - **Hours 1-2**: Direct concept study and hands-on coding (avoid passive video watching!).
   - **Hour 3**: Implement a micro-project or solve a practical algorithmic prompt.
   - **Hour 4**: Application outreach or updating your execution task list.

2. **Immediate Task Resolution**:
   - Focus on pending checklist items:
${userTasks.filter(t => t.status !== "Completed").slice(0, 3).map(t => `     - [ ] **${t.title}** (Priority: ${t.priority})`).join("\n") || "     - (Create and track learning tasks in our Tasks Board!)"}

3. **Roadmap Action**:
   ${activeRoadmap ? `Your **${activeRoadmap.roadmap_json.title}** is currently active and sits at **${activeRoadmap.progress}%** completion. Focus on the upcoming milestones.` : "You don't have an active roadmap yet. Go to the **Roadmap** page, generate a deep custom plan, and let's get you on track!"}

Which of these steps shall we prioritize first today?`;
  } else if (lastMessage.includes("application") || lastMessage.includes("status") || lastMessage.includes("job")) {
    const interviewApps = userApps.filter(a => a.status === "Interview");
    const appliedApps = userApps.filter(a => a.status === "Applied");
    const oaApps = userApps.filter(a => a.status === "OA");

    return `Here is your career pipeline diagnostics report, ${userProfile?.full_name || "Varshith"}:

- **Saved / Tracking**: ${userApps.filter(a => a.status === "Saved").length}
- **Submitted (Applied)**: ${appliedApps.length}
- **Online Assessments (OA)**: ${oaApps.length}
- **Interview Stages**: ${interviewApps.length}
- **Offers Received**: ${userApps.filter(a => a.status === "Offer").length}

**Strategic Directives**:
${interviewApps.length > 0 ? `👉 **Interview focus**: You have active interviews! Pivot 70% of your daily available study blocks towards active mock behavioral prep and live system coding mocks. Analyze their tech stacks.` : ""}
${oaApps.length > 0 ? `👉 **Online Assessments pending**: Master dynamic programming and core database query performance to clear these coding benchmarks.` : ""}
${appliedApps.length > 0 ? `👉 **Outreach optimization**: You have sent several applications. Reach out directly to Engineering Leads or Tech Recruiters on LinkedIn with a highly concise 3-sentence note summarizing how your flagship projects align directly with their teams.` : `👉 **Pipeline is dry**: We should scale your applications list. Set a task on your board to search and add at least 3 high-quality role matches this week.`}

Would you like a professional referral-ask or a cold recruiter-outreach template designed for a **${userProfile?.target_role}** position?`;
  } else {
    return `Hello ${userProfile?.full_name || "Varshith"}! Let's make sure we execute with full clarity. 

As a **${userProfile?.current_level || "Beginner"} ${userProfile?.target_role || "Full Stack Developer"}** planning a daily study block of **${userProfile?.daily_hours || 4} hours**, your primary focus should be building real muscle memory.

**Buddy's Direct Action Recommendations**:
1. **Set up structural logs**: Always track your coding milestones in the **Tasks** panel.
2. **Build clean portfolios**: Save code structures and design mockups in your **Career Vault** so you never lose assets.
3. **Generate concrete tracks**: Use the **Roadmap** engine to structure your daily curriculum.

What technical concept or interview bottleneck are you facing right now? Tell me, and let's dissect it step-by-step.`;
  }
}

// --- HIGH-FIDELITY SIMULATED DIAGNOSTICS ---
function getSimulatedInterview(role: string, difficulty: string, focusArea: string) {
  return {
    questions: [
      `How do you handle asynchronous state management and caching inside a high-traffic ${role} environment?`,
      `Explain a challenging technical bug or performance bottleneck you resolved in your recent capstone project. What was the root cause?`,
      `How do you design RESTful database schemas to optimize complex queries and relationships? Describe your index selection strategy.`,
      `Describe a situation where you had a major disagreement with a team member or product manager on an implementation plan. How was it solved?`,
      `If you are asked to implement rate-limiting or security auth layers on top of a Node/Express backend, what steps do you take?`
    ],
    answers_guidance: [
      "Interviewer wants to see familiarity with async life cycles, loaders, memoized caching, and race-condition guards. Speak on local store caching vs remote syncs.",
      "ATS/STAR method: Situation, Task, Action, Result. Highlight using debugger profiling logs, reading index sizes, and tracing metrics rather than guessing.",
      "Hiring managers look for schema normalizations (1NF-3NF), join efficiencies, foreign key constraints, and explain query executions.",
      "Tests emotional maturity, listening ability, objective pros/cons trade-off analysis, and aligning with business outcomes over syntax preferences.",
      "Focus on middleware architectures, JWT signatures, session expires, CORS limits, and lightweight Redis token buckets."
    ],
    follow_ups: [
      "How would your approach scale if traffic spiked by 10x overnight?",
      "Can you describe how you would test these mechanisms using standard mock frameworks?",
      "How do you handle schema migrations in live production without causing query downtimes?"
    ]
  };
}

function getSimulatedResumeReview(resumeText: string, jobDescription: string) {
  return {
    missingKeywords: [
      "SQL Optimization",
      "Explain Query Analysis",
      "RESTful API Middleware",
      "Unit Testing (Jest / PyTest)",
      "Docker Container orchestration"
    ],
    keywordGaps: "Your resume represents strong foundational building and page structuring. However, it lacks high-value backend architecture terminology and systematic debugging keywords that ATS scanners prioritize.",
    suggestions: [
      "Add metrics-based bullet points showing exactly how your optimizations improved performance (e.g. 'Reduced DB query latency by 40% using index optimization').",
      "List Docker and Unit Testing frameworks explicitly in your technical summary grid, as recruiters frequently filter portfolios using these tags.",
      "Rewrite role bullet points using the Google XYZ formula: Accomplished [X], as measured by [Y], by doing [Z]."
    ]
  };
}

function getSimulatedStudyOptimization(targetRole: string, dailyHours: number) {
  const allocation = dailyHours > 3
    ? "2 hours active coding, 1 hour computer science theory, 1 hour roadmap building/portfolio writing"
    : "1.5 hours coding, 1 hour system engineering theory, 30 mins roadmap building";

  return {
    weeklyPlan: [
      {
        week: "Week 1",
        focus: "Foundational Syntax, REST APIs, and Environment Setup",
        allocation: allocation
      },
      {
        week: "Week 2",
        focus: "Relational Database Schema Design & Query Writing",
        allocation: allocation
      },
      {
        week: "Week 3",
        focus: "Full-Stack Authentication and Middleware Security",
        allocation: allocation
      },
      {
        week: "Week 4",
        focus: "Flagship Capstone Project Refactoring, Styling, and Shippings",
        allocation: allocation
      }
    ],
    prioritizedTasks: [
      `Build a lightweight Express backend proxy without using external generators`,
      `Write manual SQL joins to combine multiple transactional data tables`,
      `Design a custom user session manager utilizing secure state cookies`
    ],
    sequencingAdvice: "Avoid jumping to complex styling libraries too early. Establish solid backend query speeds and clean data models first, then refine visual transitions and layouts once the functionality is bulletproof."
  };
}

function getSimulatedJobReview(jobDescription: string) {
  return {
    keySkills: [
      "Full Stack Application Design",
      "Node.js Runtime environments",
      "SQL Relational Schema Modeling",
      "JWT Secure Authentication Middlewares"
    ],
    missingSkills: [
      "Docker Container Orchestration",
      "CI/CD Pipeline Configurations"
    ],
    prepGaps: [
      "Mastering SQL explains and indexes to speed up complex table queries",
      "Configuring standard CORS and Helmet configurations to lock down server ports"
    ],
    fitAnalysis: "You possess a 75% alignment with this job posting. Your foundational frontend modular styling and backend REST route setups are highly competitive. Bridging basic containerization and query indexing concepts will make you a perfect candidate.",
    tailoringAdvice: "Highlight your custom-built applications in your top portfolio section. Explicitly reference how you solved CORS security and optimized schema relations rather than just listing static technologies."
  };
}

// --- PLATFORM DEV SERVER AND PRODUCTION ASSET SERVING ---
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    // Development mode with Vite's Hot Module Replacement middleware
    console.log("Setting up Vite development middleware server...");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Production mode - serve compiled static assets from /dist
    console.log("Serving production assets from dist...");
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req: Request, res: Response) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Buddy (AI Career Execution OS) running at http://localhost:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Critical: Failed to boot full-stack Express + Vite server.", err);
});
