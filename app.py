import os
import json
import base64
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from google import genai
from google.genai import types

import db

# Page Config
st.set_page_config(
    page_title="Buddy - AI Career Execution OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to match modern visual theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Elegant Cards */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-saved { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .badge-applied { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-oa { background-color: #fefce8; color: #a16207; border: 1px solid #fef08a; }
    .badge-interview { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .badge-rejected { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
    .badge-offer { background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
    
    .badge-high { background-color: #fef2f2; color: #b91c1c; }
    .badge-medium { background-color: #fffbeb; color: #b45309; }
    .badge-low { background-color: #f0fdf4; color: #15803d; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "user" not in st.session_state:
    st.session_state["user"] = None
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "landing"
if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

# Helper: Fetch AI Client
@st.cache_resource
def get_ai_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and api_key != "MY_GEMINI_API_KEY":
        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            st.warning(f"Error initializing Gemini Client: {e}")
    return None

ai_client = get_ai_client()

# --- HIGH FIDELITY AI SIMULATIONS & FALLBACKS ---

def get_simulated_roadmap(role: str, level: str, hours: int, duration: int):
    # Match the JavaScript logic exactly
    week_count = int((duration + 6) / 7)
    weeks_list = []
    
    core_focus_map = {
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
    }
    
    default_focus = [
        "Core Foundations, language syntax, and basic programming concepts",
        "Intermediate practices, object-oriented concepts, and project structure",
        "Database interaction, API integration, and third-party libraries",
        "Application building, routing, state managers, and error handling",
        "Complex functionalities, state machines, and testing environments",
        "Deployment pipelines, cloud architectures, and configurations",
        "Mock technical interviews, system designs, and code optimizations",
        "Portfolio polishing, final resume preparations, and job application push"
    ]
    
    focus_list = core_focus_map.get(role, default_focus)
    
    for w in range(1, week_count + 1):
        focus_item = focus_list[(w - 1) % len(focus_list)]
        weeks_list.append({
            "week_number": w,
            "title": f"Phase {w}: {focus_item.split(',')[0]}",
            "main_focus": focus_item,
            "why_this_matters": f"This phase establishes vital milestones for a successful career transition into a {role} role.",
            "topics": [
                f"Core theoretical foundations for {focus_item.split(' and ')[0]}",
                f"Practical syntax, parameters, and structural execution patterns",
                f"Troubleshooting standard bugs, profiling memory, and optimizing logic",
            ],
            "tools": [
                "Visual Studio Code",
                "Git & GitHub Version Control",
                "PostgreSQL / Excel" if "Analyst" in role else "npm / Node.js Runtime",
                "Jupyter Notebooks / Anaconda" if "Machine" in role else "Vite Tooling"
            ],
            "practice_tasks": [
                f"Write 3 minor projects utilizing the core concepts of Phase {w}",
                f"Document your code structure and commit changes to a public GitHub repository",
                f"Complete 5 practical debugging challenges related to modern implementation workflows"
            ],
            "mini_project": f"Flagship Milestone {w} - Fully operational {role} subsystem",
            "daily_plan": [
                "Day 1: Read theoretical framework, take code notes, set up environment.",
                "Day 2: Write basic configurations, experiment with code syntaxes.",
                "Day 3: Integrate data elements, handle simple logical constraints.",
                "Day 4: Implement state storage, perform incremental execution checks.",
                "Day 5: Build a modular sub-component, refactor for neat spacing.",
                "Day 6: Test performance, resolve compiler warnings, build mini-project.",
                "Day 7: Document implementation logic in README, plan upcoming objectives."
            ],
            "revision_tasks": [
                "Review syntax logs from the beginning of this week.",
                "Solve one coding assessment question blind without documentation help."
            ],
            "expected_outcome": f"High level of comfort with {focus_item.split(',')[0]} and standard tooling."
        })
        
    return {
        "title": f"{duration}-Day Intensive {role} Execution Plan",
        "target_role": role,
        "current_level": level,
        "duration_days": duration,
        "daily_hours": hours,
        "overall_strategy": f"A mentor-designed curriculum tailored for {level} level. By committing {hours} hours daily, you build a robust software portfolio, master core technical concepts, and prepare for interviews using a highly focused project-based schedule.",
        "expected_outcome": f"By the end of day {duration}, you will have compiled a comprehensive technical portfolio containing at least 3 flagship projects, established complete fluency in {role} methodologies, and secured full competency for entry-to-mid level job interviews.",
        "weeks": weeks_list,
        "projects_to_build": [
            f"Flagship Capstone Project: A secure high-performance {role} platform",
            f"Full-Featured Client Portal: Real-time interactive dashboard mapping domain-specific KPIs",
            f"Technical Utility Suite: Lightweight microservices demonstrating OOP or clean architectures"
        ],
        "portfolio_resume_advice": [
            f"Optimize GitHub profiles with descriptive READMEs containing gifs, deployment instructions, and engineering breakdowns.",
            f"Structure resumes following the XYZ format (e.g. Accomplished [X], as measured by [Y], by doing [Z]).",
            f"Highlight exact technologies matching the job criteria right in the top summary banner."
        ],
        "interview_prep_topics": [
            "Complex systems design, structural normalizations, and memory limits",
            "Dynamic programming, core data structures (hashmaps, trees, arrays), and runtime complexity",
            "Domain-specific standard questions (e.g. REST API design principles or ML loss optimization)"
        ],
        "mistakes_to_avoid": [
            "Tutorial Hell: Watching video courses endlessly without typing, creating, and compiling original code.",
            "Inconsistency: Skipping preparation days. It's better to study 2 hours daily than 10 hours once a week.",
            "Neglecting soft skills: Failing to speak out loud during technical rounds and missing behavioral alignment."
        ],
        "success_checklist": [
            "Daily study block locked in calendar",
            "Git commits pushed consistently every week",
            "At least 3 complete, functional flagship projects on live hosting",
            "15 technical interview questions mastered out loud",
            "Professional portfolio website shipped and linked on resume"
        ]
    }

def get_simulated_copilot_reply(message: str, user_profile: dict, user_apps: list, user_tasks: list, active_roadmap: dict) -> str:
    msg = message.lower()
    name = user_profile.get("full_name", "Buddy Exec") if user_profile else "Buddy Exec"
    level = user_profile.get("current_level", "Beginner") if user_profile else "Beginner"
    role = user_profile.get("target_role", "Full Stack Developer") if user_profile else "Full Stack Developer"
    hours = user_profile.get("daily_hours", 4) if user_profile else 4
    
    if any(k in msg for k in ["focus", "do next", "week", "priority"]):
        pending = [t for t in user_tasks if t["status"] != "Completed"]
        tasks_bullets = "\n".join([f"     - [ ] **{t['title']}** (Priority: {t['priority']})" for t in pending[:3]])
        if not tasks_bullets:
            tasks_bullets = "     - (Create and track learning tasks in our Tasks Board!)"
            
        roadmap_str = f"Your **{active_roadmap['roadmap_json']['title']}** is currently active and sits at **{active_roadmap['progress']}%** completion." if active_roadmap else "You don't have an active roadmap yet. Go to the **Roadmap** page, generate a deep custom plan, and let's get you on track!"
        
        return f"""Let's map out your high-priority execution targets, **{name}**. Based on your profile as an **{level} {role}**:

1. **Daily Routine (Aim for {hours} hours)**:
   - **Hours 1-2**: Direct concept study and hands-on coding (avoid passive video watching!).
   - **Hour 3**: Implement a micro-project or solve a practical algorithmic prompt.
   - **Hour 4**: Application outreach or updating your execution task list.

2. **Immediate Task Resolution**:
   - Focus on pending checklist items:
{tasks_bullets}

3. **Roadmap Action**:
   {roadmap_str}

Which of these steps shall we prioritize first today?"""

    elif any(k in msg for k in ["application", "status", "job", "track"]):
        interviews = len([a for a in user_apps if a["status"] == "Interview"])
        applied = len([a for a in user_apps if a["status"] == "Applied"])
        oa = len([a for a in user_apps if a["status"] == "OA"])
        saved = len([a for a in user_apps if a["status"] == "Saved"])
        offers = len([a for a in user_apps if a["status"] == "Offer"])
        
        directives = []
        if interviews > 0:
            directives.append(f"👉 **Interview focus**: You have active interviews! Pivot 70% of your daily available study blocks towards active mock behavioral prep and live system coding mocks. Analyze their tech stacks.")
        if oa > 0:
            directives.append(f"👉 **Online Assessments pending**: Master dynamic programming and core database query performance to clear these coding benchmarks.")
        if applied > 0:
            directives.append(f"👉 **Outreach optimization**: You have sent several applications. Reach out directly to Engineering Leads or Tech Recruiters on LinkedIn with a highly concise 3-sentence note summarizing how your flagship projects align directly with their teams.")
        else:
            directives.append(f"👉 **Pipeline is dry**: We should scale your applications list. Set a task on your board to search and add at least 3 high-quality role matches this week.")
            
        directives_str = "\n".join(directives)
        
        return f"""Here is your career pipeline diagnostics report, **{name}**:

- **Saved / Tracking**: {saved}
- **Submitted (Applied)**: {applied}
- **Online Assessments (OA)**: {oa}
- **Interview Stages**: {interviews}
- **Offers Received**: {offers}

**Strategic Directives**:
{directives_str}

Would you like a professional referral-ask or a cold recruiter-outreach template designed for a **{role}** position?"""

    return f"""Hello **{name}**! I'm Buddy, your elite Career Copilot and executive career coach.

Based on your profile, you are preparing to land a **{role}** role as an **{level}**.

I am here to help you:
- Structure your daily studies and track consistency.
- Review resumes for ATS keyword matches.
- Guide you through mock interviews.
- Keep your execution task pipeline flawless.

Ask me anything about your current study plan, application strategy, or technical concepts, and I will output crisp, objective, action-driven directives!"""

def get_simulated_interview(role: str, difficulty: str, focus: str):
    return {
        "questions": [
            f"Explain the primary architecture differences and scaling bottlenecks for a modern production-ready {role} application.",
            f"Walk me through a time you had to optimize resource overhead, render speeds, or data query constraints. What parameters did you benchmark?",
            f"How do you configure and secure your development environment pipelines (e.g. env files, token exchanges, deployment containers) for a team of developers?",
            f"If you were asked to integrate a complex third-party system (like an AI model or real-time analytics stream), how would you structure the middleware adapters?",
            f"Tell me about a time you had a technical disagreement with a peer or mentor. How did you align on the engineering trade-offs?"
        ],
        "answers_guidance": [
            "Top-tier candidates explain caching strategies (Redis), data indexing optimizations, database connection pool tuning, or DOM re-rendering limits depending on the stack.",
            "Focus heavily on metrics. Mention quantitative improvements (e.g. 'reduced latency by 45%', 'shrank bundle sizes by 120kb', 'rewrote index loops from O(N^2) to O(N)').",
            "Discuss secure variable management, multi-stage Dockerfiles, branch-specific CI/CD keys, automated unit-testing hooks, and absolute token validation.",
            "Mention the Gateway or Adapter design pattern. Discuss handling async queues, retry limits, circuit-breakers, and decoupling payloads through robust serializers.",
            "Highlight emotional intelligence. Show structured testing, referencing objective metrics rather than personal opinions, and working collaboratively towards standard benchmarks."
        ],
        "follow_ups": [
            "How does your database normalization scale once you cross 10 million relational rows?",
            "Can you draw out the data flow from client requests to server adapters out loud?",
            "What security mechanisms protect your APIs from persistent DDoS or brute-force logins?"
        ]
    }

def get_simulated_resume_review(resume: str, job_desc: str):
    return {
        "missingKeywords": [
            "CI/CD Pipeline Automation",
            "PostgreSQL Database Normalization",
            "Microservices Adapter Architecture",
            "Test Driven Development (TDD)",
            "Scalable API Optimization",
            "System Benchmarking & Latency Logs"
        ],
        "keywordGaps": "The resume focuses heavily on passive code construction but completely lacks active engineering metrics. There is limited mention of system scalability, test suites, or performance optimization indicators.",
        "suggestions": [
            "Convert bullet points into XYZ formats (e.g., 'Optimized Express router hooks resulting in 30% faster token verification times').",
            "Explicitly list test suites (Jest, PyTest, or Playwright) right alongside your project definitions.",
            "Add a clean technical skills block grouping elements by category: Languages, Frameworks, Core Databases, and System Utilities."
        ]
    }

def get_simulated_study_optimization(role: str, hours: int):
    return {
        "weeklyPlan": [
            {"week": "Week 1", "focus": "Syntax deep-dives, operational variables, and algorithmic basics", "allocation": f"{hours * 4} hours core study, {hours * 3} hours practice labs"},
            {"week": "Week 2", "focus": "Database normalization, relational query speeds, and API integrations", "allocation": f"{hours * 3} hours study, {hours * 4} hours integration projects"},
            {"week": "Week 3", "focus": "Flagship Capstone assembly, state setups, and route validations", "allocation": f"{hours * 2} hours study, {hours * 5} hours direct coding"},
            {"week": "Week 4", "focus": "Unit testing, deployment optimizations, and system design reviews", "allocation": f"{hours * 2} hours testing, {hours * 5} hours prep reviews"}
        ],
        "prioritizedTasks": [
            f"Lock down {role} core framework lifecycle methods",
            "Write standard query routines without an ORM layer to master parameters",
            "Deploy your current portfolio assets onto high-performance static or docker hostings"
        ],
        "sequencingAdvice": f"Focus purely on a single flagship project this month. Dedicate the first 50% of your daily {hours}-hour study window to reading standard specifications, and the remaining 50% to compiling and committing functional components."
    }

def get_simulated_job_review(job_desc: str):
    return {
        "keySkills": ["RESTful API Integration", "System Security & Token Exchange", "TypeScript Fluency", "Relational Database Performance"],
        "missingSkills": ["Automated Unit Testing Suites", "System Architecture Documentation", "Production container configurations (Docker)"],
        "prepGaps": ["Review horizontal scaling limits", "Master JWT security pipelines and CORS configurations out loud", "Practice live dynamic-programming challenges under time-limit pressures"],
        "fitAnalysis": "This job requires high independence and structured output. There is a strong emphasis on full lifecycle delivery, database queries, and secure integration adapters.",
        "tailoringAdvice": "Highlight your flagship capstone project right at the top of your portfolio README. Explicitly list your testing configurations and deployment steps to prove complete autonomy."
    }

# --- LANDING PAGE VIEW ---

def show_landing_page():
    st.markdown("""
    <div style="text-align: center; padding: 40px 10px;">
        <span style="background-color: #eff6ff; color: #1d4ed8; padding: 6px 16px; border-radius: 9999px; font-size: 13px; font-weight: 600;">
            ✨ The Career OS for High Performers
        </span>
        <h1 class="main-title" style="font-size: 48px; margin-top: 15px; margin-bottom: 15px; color: #0f172a;">
            The AI Career <span style="color: #2563eb;">Execution OS</span> for Students & Freshers
        </h1>
        <p style="font-size: 18px; color: #475569; max-width: 700px; margin: 0 auto 30px auto; line-height: 1.6;">
            Buddy helps students, freshers, and job switchers organize their career vault, track professional applications, build real-time study goals, and execute daily with absolute clarity.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="metric-card" style="margin-bottom: 20px;">
            <h3 style="color: #0f172a; margin-top: 0;">🚀 Unified Workspace Modules</h3>
            <p style="color: #475569; font-size: 14px;">Buddy acts as your centralized commander, coordinating every single asset of your career preparation.</p>
            <ul style="font-size: 14px; color: #334155; line-height: 1.8;">
                <li>📂 <b>Career Document Vault:</b> Store, tag, and organize resumes, certs, and project notes.</li>
                <li>💼 <b>Application Pipeline:</b> Real-time tracking of jobs, interviews, OAs, and offers.</li>
                <li>📋 <b>Task Execution Board:</b> Interactive to-dos with priorities, deadlines, and direct roadmap integrations.</li>
                <li>🗺️ <b>AI Custom Roadmaps:</b> Tailor-made week-by-week technical curriculums based on target hours.</li>
                <li>💬 <b>Buddy Career Copilot:</b> Context-aware elite chat assistant to diagnose pipelines and review posts.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card" style="margin-bottom: 20px;">
            <h3 style="color: #b91c1c; margin-top: 0;">⚠️ The Job Prep Struggle is Real</h3>
            <p style="color: #475569; font-size: 14px;">Most platforms tell you what jobs exist. Buddy tells you how to prepare and actually execute to land them.</p>
            <ul style="font-size: 14px; color: #334155; line-height: 1.8;">
                <li>❌ <b>Tutorial Hell:</b> We waste hours parsing endless playlists, skipping frameworks randomly.</li>
                <li>❌ <b>Scattered Assets:</b> Resumes, certs, and files are lost inside Google Drive or download files.</li>
                <li>❌ <b>Loss of Consistency:</b> Applying randomly with no clear daily commitment patterns.</li>
                <li>❌ <b>No Structured Mentor:</b> Standard guides are generic. Buddy generates tailored plans.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 40px 0;'>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center; color: #0f172a;'>Join your workspace to kickstart execution</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("🚪 Log In to Account", use_container_width=True, type="primary"):
                st.session_state["current_page"] = "auth"
                st.session_state["auth_mode"] = "login"
                st.rerun()
        with sc2:
            if st.button("📝 Register New Workspace", use_container_width=True):
                st.session_state["current_page"] = "auth"
                st.session_state["auth_mode"] = "signup"
                st.rerun()

# --- AUTHENTICATION VIEW ---

def show_auth_page():
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <h2 class="main-title" style="text-align: center; margin-top: 0; color: #0f172a;">
                {"Buddy Career OS Sign In" if st.session_state["auth_mode"] == "login" else "Create Buddy Workspace"}
            </h2>
            <p style="text-align: center; color: #64748b; font-size: 14px; margin-bottom: 25px;">
                {"Access your personal career curator and pipeline tracker." if st.session_state["auth_mode"] == "login" else "Set up your custom career vault and task board."}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("auth_form"):
            email = st.text_input("Corporate or University Email", placeholder="your.name@example.com")
            password = st.text_input("Secure Password", type="password", placeholder="••••••••")
            full_name = ""
            if st.session_state["auth_mode"] == "signup":
                full_name = st.text_input("Your Full Name", placeholder="Varshith")
                
            submit_label = "Sign In" if st.session_state["auth_mode"] == "login" else "Create Workspace"
            submitted = st.form_submit_button(submit_label, use_container_width=True, type="primary")
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in all requested fields.")
                elif st.session_state["auth_mode"] == "signup" and not full_name:
                    st.error("Please provide your full name.")
                else:
                    if st.session_state["auth_mode"] == "login":
                        res = db.login(email, password)
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            st.session_state["user"] = res["user"]
                            st.session_state["current_page"] = "dashboard"
                            st.success("Welcome back to Buddy! Redirecting...")
                            st.rerun()
                    else:
                        res = db.signup(email, password, full_name)
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            st.success("Account created successfully! Log in to get started.")
                            st.session_state["auth_mode"] = "login"
                            st.rerun()
                            
        # Switch mode button
        if st.session_state["auth_mode"] == "login":
            if st.button("New to Buddy? Create a free workspace", use_container_width=True):
                st.session_state["auth_mode"] = "signup"
                st.rerun()
        else:
            if st.button("Already have a workspace? Log in", use_container_width=True):
                st.session_state["auth_mode"] = "login"
                st.rerun()
                
        if st.button("⬅ Back to Home", use_container_width=True):
            st.session_state["current_page"] = "landing"
            st.rerun()

# --- MAIN APP ROUTING (SIDEBAR) ---

def show_app_navigation(user_id):
    profile = db.get_profile(user_id)
    name = profile.get("full_name", "User") if profile else "User"
    role = profile.get("target_role", "Full Stack Developer") if profile else "Full Stack Developer"
    
    st.sidebar.markdown(f"""
    <div style="padding: 10px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;">
        <h3 class="main-title" style="margin: 0; color: #1e3a8a; display: flex; align-items: center; gap: 8px;">
            🎯 Buddy OS
        </h3>
        <p style="margin: 5px 0 0 0; font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">
            Career Execution OS
        </p>
    </div>
    <div style="padding: 5px 0 15px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;">
        <span style="font-weight: 700; color: #0f172a; font-size: 14px;">{name}</span><br>
        <span style="color: #2563eb; font-size: 12px; font-weight: 500;">{role}</span>
    </div>
    """, unsafe_allow_html=True)
    
    pages = {
        "dashboard": "🏠 Dashboard Center",
        "vault": "📁 Career Vault (Files)",
        "applications": "💼 Application Tracker",
        "roadmap": "🗺️ Custom AI Roadmap",
        "tasks": "📋 Tasks Board",
        "buddy-ai": "💬 Buddy AI Coach & Tools",
        "profile": "👤 My Profile & Settings"
    }
    
    active_btn = st.session_state.get("active_tab", "dashboard")
    
    for key, val in pages.items():
        if st.sidebar.button(val, use_container_width=True, type="primary" if active_btn == key else "secondary"):
            st.session_state["active_tab"] = key
            st.rerun()
            
    st.sidebar.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout Workspace", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["current_page"] = "landing"
        st.session_state["active_tab"] = "dashboard"
        st.rerun()

# --- MODULE 1: DASHBOARD ---

def show_dashboard(user_id):
    profile = db.get_profile(user_id) or {}
    name = profile.get("full_name", "User")
    target_role = profile.get("target_role", "Full Stack Developer")
    
    apps = db.get_applications(user_id)
    tasks = db.get_tasks(user_id)
    documents = db.get_documents(user_id)
    roadmaps = db.get_roadmaps(user_id)
    active_roadmap = roadmaps[0] if roadmaps else None
    
    # Calculate counts & progress
    total_apps = len(apps)
    pending_tasks_count = len([t for t in tasks if t["status"] != "Completed"])
    docs_count = len(documents)
    roadmap_progress = active_roadmap["progress"] if active_roadmap else 0
    
    st.markdown(f"""
    <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 25px;">
        <h1 class="main-title" style="margin: 0; color: #0f172a; font-size: 28px;">Good morning, {name} 👋</h1>
        <p style="margin: 5px 0 0 0; color: #64748b; font-size: 13px;">
            Here is your Career OS diagnostic. Current target role is set to <b><span style="color: #2563eb; text-decoration: underline;">{target_role}</span></b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Grid of Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <span style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;">📂 Stored Vault Files</span>
            <h2 style="margin: 10px 0 0 0; color: #0f172a; font-size: 28px;">{docs_count}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <span style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;">💼 Job Pipelines</span>
            <h2 style="margin: 10px 0 0 0; color: #0f172a; font-size: 28px;">{total_apps}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <span style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;">📋 Active Study Tasks</span>
            <h2 style="margin: 10px 0 0 0; color: #0f172a; font-size: 28px;">{pending_tasks_count}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <span style="color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase;">🗺️ Roadmap Completion</span>
            <h2 style="margin: 10px 0 0 0; color: #0f172a; font-size: 28px;">{roadmap_progress}%</h2>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Recommendation Banner
    def get_buddy_insight():
        if not active_roadmap:
            return {
                "title": "🗺️ Initialize your custom strategy",
                "text": f"Hello {name}! You don't have an active preparation roadmap generated yet. Generate a 30, 60, or 90-day track for {target_role} to structure your studies.",
                "label": "Generate Roadmap",
                "page": "roadmap"
            }
        
        completed_tasks = [t for t in tasks if t["status"] == "Completed"]
        if not completed_tasks and pending_tasks_count > 0:
            return {
                "title": "📋 Kickstart your execution pipeline",
                "text": f"You have {pending_tasks_count} active study targets pending. Let's finish your highest priority task first today to build consistency.",
                "label": "View Task Board",
                "page": "tasks"
            }
            
        interviews_count = len([a for a in apps if a["status"] == "Interview"])
        if interviews_count > 0:
            return {
                "title": "💬 Interview Prep Overdrive",
                "text": f"You have active interview loops with {interviews_count} companies! Set aside 1 hour today in Buddy AI to simulate mock behavioral templates.",
                "label": "Chat with Buddy AI",
                "page": "buddy-ai"
            }
            
        if total_apps > 4:
            return {
                "title": "🔍 Consolidate application assets",
                "text": f"You've applied to {total_apps} roles so far. Review your matching resume keywords inside Career Vault to maximize response rates.",
                "label": "Open Vault",
                "page": "vault"
            }
            
        return {
            "title": "🔥 Keep the streak going",
            "text": f"Your {active_roadmap['role']} preparation track is at {roadmap_progress}% progress. Follow Phase 1 mini-projects to lock in intermediate skills.",
            "label": "View Roadmap Phase",
            "page": "roadmap"
        }
        
    insight = get_buddy_insight()
    
    st.info(f"**{insight['title']}**\n\n{insight['text']}")
    if st.button(insight["label"], type="primary"):
        st.session_state["active_tab"] = insight["page"]
        st.rerun()
        
    st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 25px 0;'>", unsafe_allow_html=True)
    
    c_left, c_right = st.columns([1.2, 0.8])
    with c_left:
        st.markdown("<h3 class='main-title' style='color: #0f172a; margin-top: 0;'>🎯 Today's Focus Checklist</h3>", unsafe_allow_html=True)
        # Filter high/medium tasks
        focus_tasks = [t for t in tasks if t["status"] != "Completed"]
        focus_tasks.sort(key=lambda x: {"High": 3, "Medium": 2, "Low": 1}.get(x["priority"], 0), reverse=True)
        
        if not focus_tasks:
            st.write("All tasks completed! Add new targets on the **Tasks Board**.")
        else:
            for t in focus_tasks[:4]:
                tc1, tc2 = st.columns([0.1, 0.9])
                with tc1:
                    # Toggle completion directly
                    if st.checkbox("", key=f"dash_task_{t['id']}"):
                        db.update_task(user_id, t["id"], {"status": "Completed"})
                        st.success(f"Completed: {t['title']}!")
                        st.rerun()
                with tc2:
                    st.markdown(f"**{t['title']}** <span class='badge badge-{'high' if t['priority']=='High' else ('medium' if t['priority']=='Medium' else 'low')}' style='margin-left: 10px;'>{t['priority']}</span><br><span style='font-size: 12px; color: #64748b;'>Due: {t['due_date']}</span>", unsafe_allow_html=True)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    
    with c_right:
        st.markdown("<h3 class='main-title' style='color: #0f172a; margin-top: 0;'>📅 Upcoming Events</h3>", unsafe_allow_html=True)
        events = [a for a in apps if a["status"] in ["Interview", "OA"] or a.get("deadline")]
        if not events:
            st.write("No upcoming events or deadlines logged.")
        else:
            for ev in events[:3]:
                badge_style = "badge-interview" if ev["status"] == "Interview" else "badge-oa" if ev["status"] == "OA" else "badge-saved"
                st.markdown(f"""
                <div style="background-color: #fafbfc; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 6px; margin-bottom: 12px; border: 1px solid #e2e8f0; border-left-width: 4px;">
                    <span class="badge {badge_style}" style="float: right;">{ev['status']}</span>
                    <strong style="color: #0f172a; font-size: 14px;">{ev['company']}</strong><br>
                    <span style="font-size: 12px; color: #475569;">{ev['role']}</span><br>
                    <span style="font-size: 11px; color: #94a3b8;">Deadline/Date: {ev.get('deadline') or ev.get('date_applied')}</span>
                </div>
                """, unsafe_allow_html=True)

# --- MODULE 2: CAREER VAULT ---

def show_vault(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>📁 Career Document Vault</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Manage, preview, and organize all your resume variants, certificates, projects, and study notes in a central storage space.</p>", unsafe_allow_html=True)
    
    docs = db.get_documents(user_id)
    
    with st.expander("📥 Add New Document to Vault", expanded=False):
        with st.form("add_doc_form"):
            title = st.text_input("Document Name / Title", placeholder="e.g. Varshith Resume SDE")
            category = st.selectbox("Category", ["Resume", "Certificates", "Projects", "Notes", "Academic", "Other"])
            file_type = st.selectbox("Format", ["pdf", "docx", "md", "png", "jpg", "zip"])
            tags_input = st.text_input("Tags (comma separated)", placeholder="sde, fullstack, backend")
            
            # Allow text content for notes, or file upload
            doc_content_type = st.radio("Document Input Method", ["Text Notes / Markdown Content", "Upload File"])
            file_b64 = ""
            if doc_content_type == "Text Notes / Markdown Content":
                notes_content = st.text_area("Write/Paste Content or Markdown", placeholder="e.g. Resume summaries, notes, links...")
                if notes_content:
                    file_b64 = base64.b64encode(notes_content.encode("utf-8")).decode("utf-8")
            else:
                uploaded_file = st.file_uploader("Select file (PDF, Docx, MD, JPG, etc.)")
                if uploaded_file is not None:
                    bytes_data = uploaded_file.read()
                    file_b64 = base64.b64encode(bytes_data).decode("utf-8")
                    
            submitted = st.form_submit_button("Upload Asset to Vault", type="primary")
            if submitted:
                if not title:
                    st.error("Please provide a document title.")
                else:
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                    db.create_document(user_id, {
                        "title": title,
                        "category": category,
                        "file_type": file_type,
                        "file_url": file_b64,
                        "tags": tags
                    })
                    st.success(f"Successfully uploaded '{title}' to vault!")
                    st.rerun()
                    
    st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Document Search & Filter
    c1, c2 = st.columns([2, 1])
    with c1:
        search_query = st.text_input("🔍 Search Document Vault", placeholder="Search by name, category, or tags...")
    with c2:
        filter_cat = st.selectbox("Filter by Category", ["All Categories", "Resume", "Certificates", "Projects", "Notes", "Academic", "Other"])
        
    filtered_docs = docs
    if search_query:
        search_query = search_query.lower()
        filtered_docs = [
            d for d in filtered_docs 
            if search_query in d["title"].lower() or 
               search_query in d["category"].lower() or 
               any(search_query in t.lower() for t in d.get("tags", []))
        ]
        
    if filter_cat != "All Categories":
        filtered_docs = [d for d in filtered_docs if d["category"] == filter_cat]
        
    if not filtered_docs:
        st.info("No documents found in vault.")
    else:
        for d in filtered_docs:
            tags_html = " ".join([f"<span class='badge badge-saved' style='margin-right: 5px;'>#{t}</span>" for t in d.get("tags", [])])
            st.markdown(f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #0f172a; font-size: 15px;">📄 {d['title']}</strong> 
                    <span class="badge badge-applied" style="margin-left: 10px;">{d['category']}</span>
                    <span style="font-size: 12px; color: #94a3b8; margin-left: 15px;">Uploaded: {d['uploaded_at'][:10]}</span><br>
                    <div style="margin-top: 5px;">{tags_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            bc1, bc2, bc3 = st.columns([1, 1, 6])
            with bc1:
                # Preview notes content if base64 decodes into readable text
                if d["file_url"]:
                    try:
                        decoded_text = base64.b64decode(d["file_url"].encode("utf-8")).decode("utf-8")
                        # Show preview in popover
                        with st.popover("👁️ Preview", use_container_width=True):
                            st.text_area("File Content Preview", decoded_text, height=200, disabled=True)
                    except:
                        st.button("👁️ Preview Unavailable", key=f"prev_fail_{d['id']}", disabled=True)
            with bc2:
                if st.button("🗑️ Delete", key=f"del_doc_{d['id']}", type="secondary", use_container_width=True):
                    db.delete_document(user_id, d["id"])
                    st.success(f"Deleted Document!")
                    st.rerun()
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# --- MODULE 3: JOB APPLICATIONS ---

def show_applications(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>💼 Job Application Tracker</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Track your professional applications, from saved listings to active interviews and offer letters.</p>", unsafe_allow_html=True)
    
    apps = db.get_applications(user_id)
    
    with st.expander("➕ Log New Job Application", expanded=False):
        with st.form("add_app_form"):
            c1, c2 = st.columns(2)
            with c1:
                company = st.text_input("Company Name", placeholder="e.g. Google")
                role = st.text_input("Role / Title", placeholder="e.g. Software Engineer Intern")
                location = st.text_input("Location", placeholder="e.g. Bangalore, India (Remote)")
                job_link = st.text_input("Job Application URL", placeholder="e.g. https://careers.google.com/...")
            with c2:
                status = st.selectbox("Current Status", ["Saved", "Applied", "OA", "Interview", "Rejected", "Offer"])
                source = st.text_input("Source / Referral Info", placeholder="e.g. LinkedIn, Referral by friend")
                date_applied = st.date_input("Date Applied", datetime.today())
                deadline = st.date_input("Deadline (Optional)", datetime.today() + pd.Timedelta(days=14))
                
            stipend_or_salary = st.text_input("Compensation info (Stipend / Salary)", placeholder="e.g. ₹50k/month or $120k/yr")
            notes = st.text_area("Study notes / Interview schedules / Next steps", placeholder="e.g. OA scheduled for Next Friday. Need to master DP.")
            
            submitted = st.form_submit_button("Track Application", type="primary")
            if submitted:
                if not company or not role:
                    st.error("Company and Role are required.")
                else:
                    db.create_application(user_id, {
                        "company": company,
                        "role": role,
                        "location": location,
                        "job_link": job_link,
                        "status": status,
                        "source": source,
                        "date_applied": str(date_applied),
                        "deadline": str(deadline),
                        "stipend_or_salary": stipend_or_salary,
                        "notes": notes
                    })
                    st.success(f"Successfully tracking application for SDE {role} at {company}!")
                    st.rerun()
                    
    st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Filters & Charts
    if apps:
        app_df = pd.DataFrame(apps)
        
        # Plotly pipeline distribution chart
        st.markdown("### 📊 Application Pipeline Diagnostic")
        fig = px.bar(
            app_df.groupby("status").size().reset_index(name="count"),
            x="status", y="count",
            color="status",
            labels={"status": "Pipeline Stage", "count": "Count"},
            color_discrete_map={
                "Saved": "#64748b", "Applied": "#3b82f6", "OA": "#eab308",
                "Interview": "#22c55e", "Rejected": "#ef4444", "Offer": "#f59e0b"
            }
        )
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Filter selection
    filter_status = st.selectbox("Filter by Status", ["All Applications", "Saved", "Applied", "OA", "Interview", "Rejected", "Offer"])
    
    filtered_apps = apps
    if filter_status != "All Applications":
        filtered_apps = [a for a in apps if a["status"] == filter_status]
        
    if not filtered_apps:
        st.info("No job applications logged matching filter criteria.")
    else:
        for a in filtered_apps:
            badge_style = "badge-saved" if a["status"] == "Saved" else "badge-applied" if a["status"] == "Applied" else "badge-oa" if a["status"] == "OA" else "badge-interview" if a["status"] == "Interview" else "badge-rejected" if a["status"] == "Rejected" else "badge-offer"
            st.markdown(f"""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 10px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3 style="margin: 0; color: #0f172a; font-size: 18px;">{a['company']} <span style="font-size: 14px; font-weight: normal; color: #64748b;">({a['location']})</span></h3>
                        <p style="margin: 5px 0 0 0; font-weight: 500; color: #2563eb;">{a['role']}</p>
                    </div>
                    <span class="badge {badge_style}">{a['status']}</span>
                </div>
                <div style="margin-top: 12px; font-size: 12px; color: #475569; display: flex; gap: 20px; flex-wrap: wrap;">
                    <span>📅 Applied: {a['date_applied']}</span>
                    <span>⌛ Deadline: {a['deadline']}</span>
                    <span>💰 Compensation: {a['stipend_or_salary'] or "N/A"}</span>
                    <span>🔗 <a href="{a['job_link']}" target="_blank">Job Link</a></span>
                </div>
                <div style="margin-top: 10px; font-size: 13px; background-color: #f8fafc; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #cbd5e1; color: #334155;">
                    <b>Study notes/logs:</b> {a['notes'] or "No specific schedules written yet."}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Application Actions
            ac1, ac2, ac3, ac4 = st.columns(4)
            with ac1:
                # Quick update status
                new_st = st.selectbox("Change Status", ["Saved", "Applied", "OA", "Interview", "Rejected", "Offer"], index=["Saved", "Applied", "OA", "Interview", "Rejected", "Offer"].index(a["status"]), key=f"quick_st_{a['id']}")
                if new_st != a["status"]:
                    db.update_application(user_id, a["id"], {"status": new_st})
                    st.success("Pipeline status updated!")
                    st.rerun()
            with ac2:
                if st.button("🗑️ Remove application", key=f"del_app_{a['id']}", use_container_width=True):
                    db.delete_application(user_id, a["id"])
                    st.success("Removed application.")
                    st.rerun()
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

# --- MODULE 4: CAREER ROADMAP ---

def show_roadmap(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>🗺️ Personalized Career Roadmap</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Build an end-to-end, personalized, weekly study program customized directly for your target hours and technical background level.</p>", unsafe_allow_html=True)
    
    profile = db.get_profile(user_id) or {}
    roadmaps = db.get_roadmaps(user_id)
    active_roadmap = roadmaps[0] if roadmaps else None
    
    if not active_roadmap:
        st.markdown("""
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h4 style="margin: 0; color: #166534;">🌟 Custom Career Curator Engine</h4>
            <p style="margin: 5px 0 0 0; color: #14532d; font-size: 13px;">Specify your timeline and target role to generate a comprehensive technical curriculum with tailored daily plans and mini projects.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("generate_roadmap_form"):
            role = st.selectbox("Target Role", ["Full Stack Developer", "Backend Developer", "Frontend Developer", "Machine Learning Engineer", "Data Analyst", "Python Developer", "Software Engineer", "DevOps Engineer"])
            level = st.selectbox("Your Technical Background Level", ["Beginner", "Intermediate", "Advanced"])
            hours = st.slider("Daily Study Availability (Hours)", min_value=1, max_value=12, value=4)
            duration = st.selectbox("Target Preparation Timeline (Days)", [30, 60, 90])
            
            submitted = st.form_submit_button("Generate Specialized Plan with AI", type="primary")
            if submitted:
                with st.spinner("Generating highly structured, elite study curriculum using Gemini Flash..."):
                    # Check if Gemini API can be used
                    success = False
                    if ai_client:
                        try:
                            system_instruction = """You are an elite, practical career mentor and tech lead.
You must output your response in STRICTLY compliant JSON format matching this schema:
{
  "title": "string (Title of the roadmap)",
  "target_role": "string",
  "current_level": "string",
  "duration_days": number,
  "daily_hours": number,
  "overall_strategy": "string",
  "expected_outcome": "string",
  "weeks": [
    {
      "week_number": number,
      "title": "string",
      "main_focus": "string",
      "why_this_matters": "string",
      "topics": ["string"],
      "tools": ["string"],
      "practice_tasks": ["string"],
      "mini_project": "string",
      "daily_plan": ["string"],
      "revision_tasks": ["string"],
      "expected_outcome": "string"
    }
  ],
  "projects_to_build": ["string"],
  "portfolio_resume_advice": ["string"],
  "interview_prep_topics": ["string"],
  "mistakes_to_avoid": ["string"],
  "success_checklist": ["string"]
}"""
                            user_prompt = f"""Create a personalized career execution roadmap for:
- Role: {role}
- Level: {level}
- Available commitment: {hours} hours/day
- Duration: {duration} days"""

                            response = ai_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    response_mime_type="application/json",
                                    temperature=0.1
                                )
                            )
                            roadmap_json = json.loads(response.text.strip())
                            db.save_roadmap(user_id, {
                                "role": role,
                                "current_level": level,
                                "daily_hours": hours,
                                "duration_days": duration,
                                "roadmap_json": roadmap_json,
                                "progress": 0
                            })
                            success = True
                        except Exception as e:
                            st.warning(f"Failed to generate roadmap via Gemini API: {e}. Falling back to high-fidelity generator fallback...")
                            
                    if not success:
                        # Use local high-fidelity generator fallback
                        sim_roadmap = get_simulated_roadmap(role, level, hours, duration)
                        db.save_roadmap(user_id, {
                            "role": role,
                            "current_level": level,
                            "daily_hours": hours,
                            "duration_days": duration,
                            "roadmap_json": sim_roadmap,
                            "progress": 0
                        })
                        
                    st.success("Successfully compiled custom career execution plan!")
                    st.rerun()
    else:
        # Active Roadmap details
        roadmap_data = active_roadmap["roadmap_json"]
        
        st.markdown(f"""
        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h2 class="main-title" style="margin: 0; color: #1e40af; font-size: 24px;">🗺️ {roadmap_data['title']}</h2>
                    <p style="margin: 5px 0 0 0; color: #3b82f6; font-size: 13px;">
                        Targeting: <b>{active_roadmap['role']}</b> ({active_roadmap['current_level']} Level) | Daily commit: <b>{active_roadmap['daily_hours']} hours</b>
                    </p>
                </div>
                <div style="text-align: right;">
                    <span class="badge badge-offer" style="font-size: 14px; padding: 5px 12px;">Progress: {active_roadmap['progress']}%</span>
                </div>
            </div>
            <div style="margin-top: 15px; font-size: 14px; color: #1e3a8a; line-height: 1.6;">
                <b>Overall Strategy:</b> {roadmap_data.get('overall_strategy', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📅 Weekly Curriculums")
        for wk in roadmap_data.get("weeks", []):
            with st.expander(f"Week {wk['week_number']}: {wk['title']}", expanded=(wk['week_number'] == 1)):
                st.markdown(f"**🎯 Main Focus:** {wk['main_focus']}")
                st.markdown(f"**💡 Why This Matters:** *{wk['why_this_matters']}*")
                
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown("**📚 Topics to Master:**")
                    for top in wk.get("topics", []):
                        st.markdown(f"- {top}")
                    st.markdown("**🛠️ Tools to Leverage:**")
                    for tl in wk.get("tools", []):
                        st.markdown(f"- `{tl}`")
                with col_w2:
                    st.markdown("**🏗️ Flagship Mini-Project:**")
                    st.info(wk.get("mini_project", ""))
                    st.markdown("**🎯 Expected Output:**")
                    st.success(wk.get("expected_outcome", ""))
                    
                st.markdown("**📅 Daily Structured study allocation:**")
                for d_plan in wk.get("daily_plan", []):
                    st.markdown(f"- {d_plan}")
                    
                st.markdown("**📋 Suggested Practice Tasks:**")
                for p_task in wk.get("practice_tasks", []):
                    tc_left, tc_right = st.columns([0.8, 0.2])
                    with tc_left:
                        st.markdown(f"- {p_task}")
                    with tc_right:
                        if st.button("➕ Import Task", key=f"imp_t_{wk['week_number']}_{p_task[:20]}"):
                            db.create_task(user_id, {
                                "title": p_task,
                                "description": f"Imported from {roadmap_data['title']} (Week {wk['week_number']})",
                                "due_date": str(datetime.today().date() + pd.Timedelta(days=4)),
                                "status": "Todo",
                                "priority": "Medium",
                                "related_type": "roadmap"
                            })
                            st.success("Imported to Execution Board!")
                            
                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                if st.button(f"Mark Week {wk['week_number']} Completed", key=f"wk_comp_{wk['week_number']}", type="primary"):
                    total_weeks = len(roadmap_data["weeks"])
                    new_progress = min(100, int((wk["week_number"] / total_weeks) * 100))
                    db.update_roadmap_progress(user_id, active_roadmap["id"], new_progress)
                    st.success(f"Week {wk['week_number']} marked complete! Progress is now {new_progress}%.")
                    st.rerun()
                    
        st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;'>", unsafe_allow_html=True)
        
        # Additional resources from AI
        st.markdown("### 🏆 Flagship Projects & Interview Preparation Highlights")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("**📂 Flagship Portfolio Projects to Build:**")
            for p in roadmap_data.get("projects_to_build", []):
                st.markdown(f"1. **{p}**")
            st.markdown("**📝 Portfolio & Resume Tweaks:**")
            for r in roadmap_data.get("portfolio_resume_advice", []):
                st.markdown(f"- {r}")
        with col_r2:
            st.markdown("**💬 High-Yield Interview Prep Topics:**")
            for i in roadmap_data.get("interview_prep_topics", []):
                st.markdown(f"- {i}")
            st.markdown("**❌ Common Mistakes to Avoid:**")
            for m in roadmap_data.get("mistakes_to_avoid", []):
                st.markdown(f"- ⚠️ {m}")
                
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Reset Roadmap Curator Engine (Start Fresh)", type="secondary", use_container_width=True):
            db.delete_roadmap(user_id, active_roadmap["id"])
            st.success("Roadmap reset. Curator Engine is ready.")
            st.rerun()

# --- MODULE 5: TASKS BOARD ---

def show_tasks(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>📋 Execution Tasks Board</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Log, organize, and check off daily study goals, interview dates, and system builds.</p>", unsafe_allow_html=True)
    
    tasks = db.get_tasks(user_id)
    
    with st.expander("➕ Log New Task / Study Target", expanded=False):
        with st.form("add_task_form"):
            title = st.text_input("Task Title", placeholder="e.g. Master React useState Hook")
            description = st.text_area("Description / Links / Deliverables", placeholder="e.g. Practice 3 coding examples. Read docs.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                due_date = st.date_input("Target Date", datetime.today())
            with c2:
                priority = st.selectbox("Priority", ["High", "Medium", "Low"])
            with c3:
                status = st.selectbox("Initial Status", ["Todo", "In Progress", "Completed"])
                
            submitted = st.form_submit_button("Track Task on Board", type="primary")
            if submitted:
                if not title:
                    st.error("Please provide a task title.")
                else:
                    db.create_task(user_id, {
                        "title": title,
                        "description": description,
                        "due_date": str(due_date),
                        "priority": priority,
                        "status": status,
                        "related_type": "general"
                    })
                    st.success(f"Added task '{title}' to your execution pipeline!")
                    st.rerun()
                    
    st.markdown("<hr style='border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Kanban Board
    col_todo, col_in_progress, col_completed = st.columns(3)
    
    with col_todo:
        st.markdown("<h3 style='text-align: center; color: #475569; background-color: #f1f5f9; padding: 10px; border-radius: 8px;'>Todo 📥</h3>", unsafe_allow_html=True)
        todo_tasks = [t for t in tasks if t["status"] == "Todo"]
        if not todo_tasks:
            st.caption("No todo tasks. Add goals above!")
        else:
            for t in todo_tasks:
                badge_style = "badge-high" if t["priority"] == "High" else "badge-medium" if t["priority"] == "Medium" else "badge-low"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <span class="badge {badge_style}" style="float: right;">{t['priority']}</span>
                    <strong style="color: #0f172a; font-size: 15px;">{t['title']}</strong><br>
                    <p style="font-size: 12px; color: #475569; margin: 5px 0;">{t['description']}</p>
                    <span style="font-size: 11px; color: #94a3b8;">📅 Due: {t['due_date']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Move buttons
                move_col1, move_col2, move_col3 = st.columns(3)
                with move_col1:
                    if st.button("⚙️ Start", key=f"start_{t['id']}", use_container_width=True):
                        db.update_task(user_id, t["id"], {"status": "In Progress"})
                        st.rerun()
                with move_col2:
                    if st.button("✅ Complete", key=f"comp_{t['id']}", use_container_width=True):
                        db.update_task(user_id, t["id"], {"status": "Completed"})
                        st.rerun()
                with move_col3:
                    if st.button("🗑️ Delete", key=f"del_{t['id']}", use_container_width=True):
                        db.delete_task(user_id, t["id"])
                        st.rerun()
                        
    with col_in_progress:
        st.markdown("<h3 style='text-align: center; color: #1d4ed8; background-color: #dbeafe; padding: 10px; border-radius: 8px;'>In Progress ⚡</h3>", unsafe_allow_html=True)
        ip_tasks = [t for t in tasks if t["status"] == "In Progress"]
        if not ip_tasks:
            st.caption("No active tasks. Move ones from Todo!")
        else:
            for t in ip_tasks:
                badge_style = "badge-high" if t["priority"] == "High" else "badge-medium" if t["priority"] == "Medium" else "badge-low"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #3b82f6; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <span class="badge {badge_style}" style="float: right;">{t['priority']}</span>
                    <strong style="color: #0f172a; font-size: 15px;">{t['title']}</strong><br>
                    <p style="font-size: 12px; color: #475569; margin: 5px 0;">{t['description']}</p>
                    <span style="font-size: 11px; color: #3b82f6;">📅 Due: {t['due_date']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Move buttons
                move_col1, move_col2, move_col3 = st.columns(3)
                with move_col1:
                    if st.button("📥 Reset", key=f"reset_{t['id']}", use_container_width=True):
                        db.update_task(user_id, t["id"], {"status": "Todo"})
                        st.rerun()
                with move_col2:
                    if st.button("✅ Done", key=f"done_{t['id']}", use_container_width=True):
                        db.update_task(user_id, t["id"], {"status": "Completed"})
                        st.rerun()
                with move_col3:
                    if st.button("🗑️ Remove", key=f"rem_ip_{t['id']}", use_container_width=True):
                        db.delete_task(user_id, t["id"])
                        st.rerun()
                        
    with col_completed:
        st.markdown("<h3 style='text-align: center; color: #15803d; background-color: #dcfce7; padding: 10px; border-radius: 8px;'>Completed 🎉</h3>", unsafe_allow_html=True)
        comp_tasks = [t for t in tasks if t["status"] == "Completed"]
        if not comp_tasks:
            st.caption("No completed goals yet. Step up!")
        else:
            for t in comp_tasks:
                badge_style = "badge-high" if t["priority"] == "High" else "badge-medium" if t["priority"] == "Medium" else "badge-low"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #cbd5e1; padding: 15px; border-radius: 8px; margin-bottom: 12px; opacity: 0.85;">
                    <span class="badge {badge_style}" style="float: right;">{t['priority']}</span>
                    <strong style="color: #475569; font-size: 15px; text-decoration: line-through;">{t['title']}</strong><br>
                    <p style="font-size: 12px; color: #64748b; margin: 5px 0;">{t['description']}</p>
                    <span style="font-size: 11px; color: #94a3b8;">📅 Finished</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Move buttons
                move_col1, move_col2 = st.columns(2)
                with move_col1:
                    if st.button("📥 Reopen", key=f"reopen_{t['id']}", use_container_width=True):
                        db.update_task(user_id, t["id"], {"status": "Todo"})
                        st.rerun()
                with move_col2:
                    if st.button("🗑️ Delete", key=f"del_comp_{t['id']}", use_container_width=True):
                        db.delete_task(user_id, t["id"])
                        st.rerun()

# --- MODULE 6: BUDDY AI COACH & WORKSUITE ---

def show_buddy_ai(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>💬 Career Intelligence Center</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Utilize our state-of-the-art suite of AI coaching modules and ATS alignment review tools.</p>", unsafe_allow_html=True)
    
    profile = db.get_profile(user_id) or {}
    apps = db.get_applications(user_id)
    tasks = db.get_tasks(user_id)
    roadmaps = db.get_roadmaps(user_id)
    active_roadmap = roadmaps[0] if roadmaps else None
    
    tab_chat, tab_interview, tab_resume, tab_study, tab_job = st.tabs([
        "💬 Copilot Chat", 
        "📋 AI Mock Interview", 
        "🔍 ATS Resume Review", 
        "📅 Study Schedule Optimizer", 
        "💼 AI Job Review"
    ])
    
    # Tab 1: Copilot Chat
    with tab_chat:
        st.markdown("### 💬 Chat with Buddy AI Coach")
        history = db.get_chat_history(user_id)
        
        # Clear chat option
        if st.button("🗑️ Clear chat history", key="clear_chat"):
            db.clear_chat_history(user_id)
            st.success("Cleared convo history!")
            st.rerun()
            
        # Preset Prompt Widgets
        st.markdown("💡 *Quick Preset Prompts:*")
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            if st.button("🔍 What should I focus on this week?"):
                # Handle preset submit
                prompt = "What should I focus on this week?"
                db.add_chat_message(user_id, "user", prompt)
                
                # Fetch AI reply
                reply = ""
                if ai_client:
                    try:
                        # (System instruction composition as in Express Server)
                        system_instr = f"You are Buddy, an elite Career Copilot. Context: name: {profile.get('full_name', 'Varshith')}, role: {profile.get('target_role', 'SDE')}. Apps: {len(apps)}."
                        response = ai_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                            config=types.GenerateContentConfig(system_instruction=system_instr)
                        )
                        reply = response.text
                    except Exception as e:
                        reply = get_simulated_copilot_reply(prompt, profile, apps, tasks, active_roadmap)
                else:
                    reply = get_simulated_copilot_reply(prompt, profile, apps, tasks, active_roadmap)
                db.add_chat_message(user_id, "assistant", reply)
                st.rerun()
        with c_p2:
            if st.button("💼 Summarize my application progress"):
                prompt = "Summarize my application progress"
                db.add_chat_message(user_id, "user", prompt)
                reply = ""
                if ai_client:
                    try:
                        system_instr = f"You are Buddy, an elite Career Copilot. Context: name: {profile.get('full_name', 'Varshith')}, role: {profile.get('target_role', 'SDE')}. Apps: {len(apps)}."
                        response = ai_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                            config=types.GenerateContentConfig(system_instruction=system_instr)
                        )
                        reply = response.text
                    except Exception as e:
                        reply = get_simulated_copilot_reply(prompt, profile, apps, tasks, active_roadmap)
                else:
                    reply = get_simulated_copilot_reply(prompt, profile, apps, tasks, active_roadmap)
                db.add_chat_message(user_id, "assistant", reply)
                st.rerun()
        with c_p3:
            if st.button("📝 Give me a cover letter template"):
                prompt = f"Give me a professional cover letter template for a {profile.get('target_role', 'Full Stack Developer')} role."
                db.add_chat_message(user_id, "user", prompt)
                reply = f"Here is a cover letter template for a **{profile.get('target_role', 'Full Stack Developer')}**:\n\nDear Hiring Manager,\n\nI am writing to express my strong interest in the SDE role. I have active experience building complex projects and tracking them inside Buddy Career OS...\n\nBest regards,\n{profile.get('full_name', 'User')}"
                db.add_chat_message(user_id, "assistant", reply)
                st.rerun()
                
        # Display Conversational Feed
        for msg in history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])
                    
        # Chat input
        user_msg = st.chat_input("Ask Buddy anything about resumes, SDE queries, or consistency...")
        if user_msg:
            db.add_chat_message(user_id, "user", user_msg)
            reply = ""
            if ai_client:
                try:
                    system_instr = f"You are Buddy, an elite Career Copilot. Context: name: {profile.get('full_name', 'Varshith')}, role: {profile.get('target_role', 'SDE')}. Apps: {len(apps)}."
                    response = ai_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=user_msg,
                        config=types.GenerateContentConfig(system_instruction=system_instr)
                    )
                    reply = response.text
                except Exception as e:
                    reply = get_simulated_copilot_reply(user_msg, profile, apps, tasks, active_roadmap)
            else:
                reply = get_simulated_copilot_reply(user_msg, profile, apps, tasks, active_roadmap)
                
            db.add_chat_message(user_id, "assistant", reply)
            st.rerun()

    # Tab 2: Interview Prep
    with tab_interview:
        st.markdown("### 📋 AI Mock Interview Question Generator")
        st.markdown("<p style='font-size: 12px; color: #64748b;'>Generate elite-level interview practice blocks with diagnostic guides and potential follow-up pipelines.</p>", unsafe_allow_html=True)
        
        role_int = st.text_input("Target Position / Role", value=profile.get("target_role", "Full Stack Developer"), key="int_role_input")
        diff_int = st.selectbox("Complexity / Difficulty Level", ["Beginner", "Intermediate", "Advanced", "Elite / Tech Lead"], key="int_diff")
        focus_int = st.text_input("Focus Area Specs (Optional)", value="General Technical & Behavioral", key="int_focus")
        
        if st.button("Generate Interview Prep Block", type="primary"):
            with st.spinner("Compiling technical interview matrix..."):
                interview_res = None
                if ai_client:
                    try:
                        system_instruction = """You are an elite Tech Lead. Output response in STRICTLY compliant JSON format matching this schema:
{
  "questions": ["string"],
  "answers_guidance": ["string"],
  "follow_ups": ["string"]
}"""
                        user_prompt = f"Generate exactly 5 key interview questions for a {role_int} role. Difficulty: {diff_int}. Focus: {focus_int}."
                        response = ai_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                response_mime_type="application/json",
                                temperature=0.2
                            )
                        )
                        interview_res = json.loads(response.text.strip())
                    except Exception as e:
                        interview_res = get_simulated_interview(role_int, diff_int, focus_int)
                else:
                    interview_res = get_simulated_interview(role_int, diff_int, focus_int)
                    
                st.session_state["interview_result"] = interview_res
                
        if "interview_result" in st.session_state:
            res = st.session_state["interview_result"]
            st.markdown("#### 🎯 Generated Interview practice questions")
            for idx, q in enumerate(res.get("questions", [])):
                with st.expander(f"Question {idx+1}: {q}"):
                    st.markdown("**💡 High-Yield Answer Guidance (What top-tier candidates say):**")
                    guidances = res.get("answers_guidance", [])
                    if idx < len(guidances):
                        st.info(guidances[idx])
                        
            st.markdown("#### 💬 Recommended Follow-Up Questions")
            for f in res.get("follow_ups", []):
                st.markdown(f"- {f}")

    # Tab 3: Resume Review
    with tab_resume:
        st.markdown("### 🔍 ATS Resume Keyword Reviewer")
        st.markdown("<p style='font-size: 12px; color: #64748b;'>Paste your resume text to discover critical keyword omissions and SDE formatting optimizations.</p>", unsafe_allow_html=True)
        
        resume_txt = st.text_area("Paste Resume Text Content", height=200, placeholder="Paste your markdown or plain-text resume here...")
        jd_txt = st.text_area("Paste Target Job Description (Optional)", height=120, placeholder="Paste job posting criteria here to check direct alignment...")
        
        if st.button("Run Resume Diagnostics", type="primary"):
            if not resume_txt:
                st.error("Please paste your resume text to analyze.")
            else:
                with st.spinner("Analyzing resume against SDE standards..."):
                    resume_res = None
                    if ai_client:
                        try:
                            system_instruction = """You are an expert technical resume reviewer. Output response in STRICTLY compliant JSON format matching this schema:
{
  "missingKeywords": ["string"],
  "keywordGaps": "string",
  "suggestions": ["string"]
}"""
                            user_prompt = f"Analyze the candidate's resume text: {resume_txt}. Comparison: {jd_txt if jd_txt else 'Standard high-yield requirements for their field.'}"
                            response = ai_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    response_mime_type="application/json",
                                    temperature=0.2
                                )
                            )
                            resume_res = json.loads(response.text.strip())
                        except Exception as e:
                            resume_res = get_simulated_resume_review(resume_txt, jd_txt)
                    else:
                        resume_res = get_simulated_resume_review(resume_txt, jd_txt)
                        
                    st.session_state["resume_result"] = resume_res
                    
        if "resume_result" in st.session_state:
            res = st.session_state["resume_result"]
            st.markdown("#### 🚫 Missing High-Yield Keywords / Tech Omissions")
            cols = st.columns(3)
            for idx, kw in enumerate(res.get("missingKeywords", [])):
                cols[idx % 3].markdown(f"<span class='badge badge-rejected' style='font-size:12px; margin-bottom:10px;'>❌ {kw}</span>", unsafe_allow_html=True)
                
            st.markdown("#### 📊 ATS Formatting & Positioning Gap Analysis")
            st.warning(res.get("keywordGaps", ""))
            
            st.markdown("#### 📈 Strategic Recommendations")
            for sug in res.get("suggestions", []):
                st.markdown(f"- **{sug}**")

    # Tab 4: Study Optimizer
    with tab_study:
        st.markdown("### 📅 Study Schedule Optimizer")
        st.markdown("<p style='font-size: 12px; color: #64748b;'>Pivot your study blocks, active tasks, and milestones into a synchronized weekly agenda.</p>", unsafe_allow_html=True)
        
        role_std = st.text_input("Target Role Specs", value=profile.get("target_role", "Full Stack Developer"), key="std_role_input")
        hours_std = st.slider("Daily study capacity", min_value=1, max_value=12, value=int(profile.get("daily_hours", 4)), key="std_hours")
        
        if st.button("Optimize Study Blocks", type="primary"):
            with st.spinner("Calculating focus-block schedules..."):
                study_res = None
                if ai_client:
                    try:
                        system_instruction = """You are an expert developer productivity designer. Output response in STRICTLY compliant JSON format matching this schema:
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
}"""
                        user_prompt = f"Optimize study plan for a {role_std} learner. Commit window: {hours_std} hours/day."
                        response = ai_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                response_mime_type="application/json",
                                temperature=0.2
                            )
                        )
                        study_res = json.loads(response.text.strip())
                    except Exception as e:
                        study_res = get_simulated_study_optimization(role_std, hours_std)
                else:
                    study_res = get_simulated_study_optimization(role_std, hours_std)
                    
                st.session_state["study_result"] = study_res
                
        if "study_result" in st.session_state:
            res = st.session_state["study_result"]
            st.markdown("#### ⚡ Personalized Weekly Agenda")
            for wp in res.get("weeklyPlan", []):
                st.markdown(f"**{wp['week']}: {wp['focus']}**")
                st.caption(f"Time Allocation: {wp['allocation']}")
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                
            st.markdown("#### 🚨 Prioritized Immediate Tasks")
            for pt in res.get("prioritizedTasks", []):
                st.markdown(f"- [ ] {pt}")
                
            st.markdown("#### 💡 Mentor Advice")
            st.info(res.get("sequencingAdvice", ""))

    # Tab 5: Job Review
    with tab_job:
        st.markdown("### 💼 AI Job Posting Reviewer")
        st.markdown("<p style='font-size: 12px; color: #64748b;'>Paste any job description to unpack its hidden skills, requirements, and tailoring vectors.</p>", unsafe_allow_html=True)
        
        jd_review = st.text_area("Paste Job Description Text", height=200, key="jd_review_text")
        
        if st.button("Perform Job Diagnostic", type="primary"):
            if not jd_review:
                st.error("Please paste a job description first.")
            else:
                with st.spinner("Reviewing job requirements..."):
                    job_res = None
                    if ai_client:
                        try:
                            system_instruction = """You are a recruiter. Output response in STRICTLY compliant JSON format matching this schema:
{
  "keySkills": ["string"],
  "missingSkills": ["string"],
  "prepGaps": ["string"],
  "fitAnalysis": "string",
  "tailoringAdvice": "string"
}"""
                            user_prompt = f"Review this job description: {jd_review}"
                            response = ai_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    response_mime_type="application/json",
                                    temperature=0.2
                                )
                            )
                            job_res = json.loads(response.text.strip())
                        except Exception as e:
                            job_res = get_simulated_job_review(jd_review)
                    else:
                        job_res = get_simulated_job_review(jd_review)
                        
                    st.session_state["job_result"] = job_res
                    
        if "job_result" in st.session_state:
            res = st.session_state["job_result"]
            st.markdown("#### 🌟 Primary Skills Highlighted")
            st.write(", ".join(res.get("keySkills", [])))
            
            st.markdown("#### 🚫 Hard Gaps / Missing Competencies")
            for ms in res.get("missingSkills", []):
                st.markdown(f"- {ms}")
                
            st.markdown("#### 📋 Fit & Tailoring Advisory")
            st.success(res.get("fitAnalysis", ""))
            st.info(res.get("tailoringAdvice", ""))

# --- MODULE 7: PROFILE & SETTINGS ---

def show_profile(user_id):
    st.markdown("<h1 class='main-title' style='color: #0f172a;'>👤 Profile & Customization Settings</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Customize SDE targets, background levels, and daily learning schedules to calibrate your Career OS dashboard.</p>", unsafe_allow_html=True)
    
    profile = db.get_profile(user_id) or {}
    
    with st.form("profile_update_form"):
        full_name = st.text_input("Full Name / Display Name", value=profile.get("full_name", ""))
        college = st.text_input("College / University", value=profile.get("college", ""))
        target_role = st.selectbox("Target SDE Role", ["Full Stack Developer", "Backend Developer", "Frontend Developer", "Machine Learning Engineer", "Data Analyst", "Python Developer", "Software Engineer", "DevOps Engineer"], index=["Full Stack Developer", "Backend Developer", "Frontend Developer", "Machine Learning Engineer", "Data Analyst", "Python Developer", "Software Engineer", "DevOps Engineer"].index(profile.get("target_role", "Full Stack Developer")))
        current_level = st.selectbox("Current Technical Skill Level", ["Beginner", "Intermediate", "Advanced"], index=["Beginner", "Intermediate", "Advanced"].index(profile.get("current_level", "Beginner")))
        daily_hours = st.slider("Daily Commitment (Hours)", min_value=1, max_value=12, value=int(profile.get("daily_hours", 4)))
        
        submitted = st.form_submit_button("Update Calibration Profile", type="primary")
        if submitted:
            db.update_profile(user_id, {
                "full_name": full_name,
                "college": college,
                "target_role": target_role,
                "current_level": current_level,
                "daily_hours": daily_hours
            })
            st.success("Calibration parameters updated!")
            st.rerun()

# --- MAIN RENDERER LOOP ---

def main():
    if st.session_state["user"] is None:
        if st.session_state["current_page"] == "landing":
            show_landing_page()
        else:
            show_auth_page()
    else:
        user_id = st.session_state["user"]["id"]
        
        # App Sidebar Navigation
        show_app_navigation(user_id)
        
        # Page Routing logic
        active_tab = st.session_state.get("active_tab", "dashboard")
        
        if active_tab == "dashboard":
            show_dashboard(user_id)
        elif active_tab == "vault":
            show_vault(user_id)
        elif active_tab == "applications":
            show_applications(user_id)
        elif active_tab == "roadmap":
            show_roadmap(user_id)
        elif active_tab == "tasks":
            show_tasks(user_id)
        elif active_tab == "buddy-ai":
            show_buddy_ai(user_id)
        elif active_tab == "profile":
            show_profile(user_id)

if __name__ == "__main__":
    main()
