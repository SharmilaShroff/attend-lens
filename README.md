# Rollcall - AI-Powered Attendance Pattern Analyzer 🎓🤖

**Problem Statement 28 | Domain: AI & ML | Hackathon Edition**

Rollcall is an end-to-end, AI-assisted attendance pattern analyzer designed for academic institutions. Rather than relying on simple attendance percentages, Rollcall analyzes attendance time-series to detect subtle risk patterns, flag at-risk students with explainable AI indicators, provide grounded LLM counselling & student chatbots, and execute automated 24-hour parent email escalations.

---

## 🌟 Key Features & Core Innovations

1. **AI/ML Attendance Pattern Analytics Engine**:
   - **Sudden Drop**: Detects sharp attendance falls over recent 14-day rolling windows compared to historical baseline.
   - **Continuous Absence**: Flags $k \ge 3$ consecutive absences.
   - **Slow Decline**: Identifies negative linear regression trend slopes over time.
   - **Slow Improvement**: Detects positive trend slopes for positive feedback.
   - **Subject-Specific Drop**: Flags students with overall attendance $\ge 70\%$ who are severely failing a single subject ($<60\%$).
   - **Missing Record Handling**: Flags low-confidence alerts when attendance records are missing ("Not marked").
   - **Semester Drop Prediction (ML)**: Logistic regression model predicting the probability of falling below the 75% threshold by semester end.

2. **Explainability & Staff Overrides**:
   - Every alert features human-readable reasons and a factor contribution breakdown.
   - Staff can override risk severity (Low, Medium, High, Critical) or dismiss alerts with mandatory reasoning.

3. **Grounded AI Counselling & Chatbot**:
   - Anthropic Claude API integration generating empathetic, supportive counselling check-ins.
   - Student AI Chatbot grounded strictly in database facts (overall %, subject breakdown, classes needed formula, safe misses) with zero hallucination.

4. **Automated 24-Hour Parent Email Escalation**:
   - APScheduler background job checking un-responded counselling cases. If a student does not reply within 24 hours, the system automatically emails the parent and records the intervention.

5. **Multi-Role Workspaces & Screenshots UI Styling**:
   - Pixel-perfect implementation matching screenshot design language: forest green theme (`#1e4d3b`), circular role picker, dual-panel login, rounded glassmorphism cards, interactive Recharts graphs.
   - **Mentor Workspace**: Class CRUD, manual & CSV/Excel student bulk upload with downloadable template, subject/teacher mapping, alert queue.
   - **Teacher Workspace**: Select/remove taught classes, student-wise attendance marking grid with Present/Absent toggle and period slots, past attendance editing with audit logging.
   - **Student Workspace**: Overall attendance bar chart (color-coded by threshold), monthly subject line graph, "Classes Needed" calculator, weekly trend sparkline, absence reason submission with proof upload.

---

## 🚀 Quick Start & Demo Walkthrough

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```
Backend will run at: `http://localhost:8000` (Swagger docs: `http://localhost:8000/docs`)

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend will run at: `http://localhost:5173/`

---

## 🔑 Demo Hackathon Login Credentials

All demo accounts come pre-seeded with 3 months of realistic attendance history (60 working days) and pre-calculated AI risk patterns.

| Role | Identifier / Email / USN | Password | Demo Persona / Pattern Case |
| :--- | :--- | :--- | :--- |
| **Mentor** | `mentor@example.com` | `password123` | Full Class & Risk Control Workspace |
| **Subject Teacher** | `teacher1@example.com` | `password123` | Class Attendance Marking & Audit Trail |
| **Student (Sudden Drop)** | `1VA21CS001` | `1VA21CS001` | Alice Smith - DBMS Sudden Drop Pattern |
| **Student (Continuous Absence)** | `1VA21CS002` | `1VA21CS002` | Bob Jones - 5 Consecutive Absences in ML |
| **Student (Slow Decline)** | `1VA21CS003` | `1VA21CS003` | Charlie Brown - Steady decline in Web Tech |
| **Student (Subject Drop)** | `1VA21CS005` | `1VA21CS005` | Evan Wright - 86% overall, but 55% in Software Eng |

---

## 📂 Project Architecture

```
rollcall-project/
├── backend/
│   ├── app/
│   │   ├── models/models.py        # SQLAlchemy ORM definitions
│   │   ├── schemas/all_schemas.py  # Pydantic validation models
│   │   ├── services/
│   │   │   ├── analytics.py        # AI/ML pattern detection & risk scoring
│   │   │   ├── counselling.py      # LLM empathetic check-in generator
│   │   │   ├── chatbot.py          # Grounded student chatbot engine
│   │   │   └── email.py            # SMTP email handler
│   │   ├── routers/                # 10 FastAPI router modules
│   │   ├── scheduler.py            # APScheduler 24h parent email escalation
│   │   ├── config.py               # Pydantic settings & .env configuration
│   │   ├── database.py             # SQLAlchemy engine (SQLite / MySQL)
│   │   └── main.py                 # FastAPI application entrypoint
│   ├── seed.py                     # Demo dataset generator with 7 test cases
│   ├── gen_schema.py               # MySQL DDL generator
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/             # Navbar, Sidebar, ExplainDrawer, ChatbotWidget
│   │   ├── pages/
│   │   │   ├── RolePicker.jsx      # Screenshot #1 Role selection
│   │   │   ├── Login.jsx           # Screenshot #2 & #3 Dual-panel Login
│   │   │   ├── staff/              # Mentor & Teacher Workspaces
│   │   │   └── student/            # Student Dashboard & Calculator
│   │   ├── api/client.js           # Axios client with JWT interceptors
│   │   └── index.css               # Design system tokens & Tailwind CSS
└── schema.sql                      # Complete DDL database schema
```

---

## 🧮 "Classes Needed" Formula
For any subject with $A$ attended classes out of $T$ total classes, the minimum consecutive upcoming classes $x$ required to achieve threshold $t = 75\%$ is calculated as:
$$x = \left\lceil \frac{t \cdot T - A}{1 - t} \right\rceil$$

---

## 🛡️ License
Built for the Hackathon Demonstration. Open-source under MIT License.
