# 🎓 Smart Learning Planner

> An AI-powered personalized academic scheduling and study planning platform built for engineering students.

**Academic Institution:** Swami Keshvanand Institute of Technology, Management & Gramothan (SKIT), Jaipur  
**Department:** Department of Computer Science & Engineering  
**Academic Year:** 2026–2027  

---

## 📌 Project Overview

**Smart Learning Planner** dynamically generates adaptive 7-day study timetables tailored to each student's semester, daily study availability, curriculum subjects, and learning targets. The platform combines secure authentication, an interactive Next.js interface, a high-performance FastAPI microservice, and Google Gemini AI to transform student onboarding inputs into structured academic milestones.

---

## 🚀 Key Features

* **Secure Authentication & RBAC:** Complete user lifecycle management with Clerk, utilizing JWKS cryptographic RS256 token verification on the backend.
* **Student Onboarding:** Interactive multi-field onboarding interface capturing semester, daily study hours, goals, and enrolled subjects.
* **AI-Driven Study Plans:** Deterministic 7-day timetable generation powered by Google Gemini (`gemini-3.6-flash`) with structured JSON schema output.
* **Persistent Storage:** Cloud PostgreSQL storage hosted on Supabase tracking user credentials and relational student profile records.
* **Automated Weekly Progress Reporting:** Integrated GitHub Actions cron workflow generating weekly Form-3 evaluation PDF reports with commit and LOC metrics.

---

## 🛠️ System Architecture & Tech Stack

| Layer | Technologies Used | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4 | Responsive student UI and client state handling |
| **Authentication** | Clerk (`@clerk/nextjs`), PyJWT | Route protection middleware and session token issuance |
| **Backend API** | FastAPI, Uvicorn, Pydantic | Asynchronous RESTful API microservice |
| **AI Engine** | Google Gemini API (`gemini-3.6-flash`), Google GenAI SDK | Prompt orchestration and deterministic JSON schedule generation |
| **Database** | Supabase (PostgreSQL) | Relational data persistence (`users`, `student_profiles`) |
| **DevOps / CI/CD** | GitHub Actions, ReportLab, Matplotlib | Automated weekly progress auditing and Form-3 PDF generation |

---
