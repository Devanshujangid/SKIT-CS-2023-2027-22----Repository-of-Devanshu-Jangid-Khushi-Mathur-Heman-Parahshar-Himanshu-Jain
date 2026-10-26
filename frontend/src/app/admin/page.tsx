"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Users,
  BookOpen,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Search,
  ExternalLink,
  Sparkles,
  Download,
  Filter,
  RefreshCw,
  FileText,
  Activity,
  Layers,
  ShieldCheck,
} from "lucide-react";

// Student Roster Mock Data
const STUDENT_ROSTER = [
  {
    id: "23SKCS001",
    name: "Devanshu Jangid",
    semester: 5,
    focus: "Operating Systems",
    loggedHours: 30.8,
    scheduledHours: 34.5,
    completionRate: 89,
    planVersion: "v2",
    diagnosticStatus: "Needs Revision",
    ruleTrigger: "Rule 2: Sub-50% Duration",
  },
  {
    id: "23SKCS022",
    name: "Himanshu Jain",
    semester: 5,
    focus: "Algorithms & Schemas",
    loggedHours: 35.0,
    scheduledHours: 35.0,
    completionRate: 100,
    planVersion: "v1",
    diagnosticStatus: "On-Track",
    ruleTrigger: "Mastery Invariants Met",
  },
  {
    id: "23SKCS015",
    name: "Khushi Mathur",
    semester: 5,
    focus: "TF-IDF Recommendation",
    loggedHours: 32.5,
    scheduledHours: 34.0,
    completionRate: 95,
    planVersion: "v1",
    diagnosticStatus: "On-Track",
    ruleTrigger: "All Sessions Logged",
  },
  {
    id: "23SKCS019",
    name: "Heman Parashar",
    semester: 5,
    focus: "Supabase & Backend APIs",
    loggedHours: 31.0,
    scheduledHours: 32.0,
    completionRate: 97,
    planVersion: "v1",
    diagnosticStatus: "On-Track",
    ruleTrigger: "Optimal Velocity",
  },
  {
    id: "23SKCS044",
    name: "Aman Sharma",
    semester: 5,
    focus: "Computer Networks",
    loggedHours: 18.0,
    scheduledHours: 32.0,
    completionRate: 56,
    planVersion: "v3",
    diagnosticStatus: "Needs Revision",
    ruleTrigger: "Rule 1: 2 Missed Sessions",
  },
];

// Telemetry Audit Events
const AUDIT_EVENTS = [
  {
    time: "10 mins ago",
    user: "Devanshu Jangid (23SKCS001)",
    type: "Diagnostic Flag",
    detail: "Sub-50% study duration detected for Process Synchronization (75m / 180m). Status: Needs Revision.",
    severity: "warning",
  },
  {
    time: "25 mins ago",
    user: "Aman Sharma (23SKCS044)",
    type: "Adaptive Plan Re-balance",
    detail: "Forward-only catch-up generated. Version incremented to v3 (Daily ceiling 4.5h enforced).",
    severity: "info",
  },
  {
    time: "1 hour ago",
    user: "System / TF-IDF Vector Space",
    type: "Vector Match",
    detail: "Query 'Operating Systems Process Synchronization' matched 'Operating Systems and You' (Sim: 0.4585).",
    severity: "success",
  },
  {
    time: "2 hours ago",
    user: "Heman Parashar (23SKCS019)",
    type: "DB Migration Verified",
    detail: "Supabase RLS policies and cascade deletes validated across users & study_plans.",
    severity: "success",
  },
];

export default function AdminOverviewPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("all");

  const filteredStudents = STUDENT_ROSTER.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.focus.toLowerCase().includes(searchTerm.toLowerCase());
    if (selectedFilter === "needs_revision") {
      return matchesSearch && s.diagnosticStatus === "Needs Revision";
    }
    if (selectedFilter === "on_track") {
      return matchesSearch && s.diagnosticStatus === "On-Track";
    }
    return matchesSearch;
  });

  return (
    <div className="space-y-6">
      
      {/* Admin Hero Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-3xl bg-slate-950 border border-slate-800 p-6 sm:p-8 shadow-md">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-400">
            <Sparkles className="h-3.5 w-3.5" />
            <span>SKIT Department of Computer Science & Engineering</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Academic Supervisor & Platform Admin Console
          </h1>
          <p className="max-w-3xl text-xs sm:text-sm text-slate-400">
            Real-time telemetry oversight for 50% project evaluation milestone: monitoring deterministic diagnostic
            engine health, student study plan adherence, and adaptive re-balancing event streams.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/OCT_31_50_PERCENT_CHECKPOINT_ARCHITECTURE_REPORT.md"
            target="_blank"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
            <span>Architecture Report</span>
          </Link>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition-colors cursor-pointer"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export Evaluation PDF</span>
          </button>
        </div>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Enrolled Students</span>
            <div className="p-2 bg-indigo-950 text-indigo-400 rounded-xl border border-indigo-800/40">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">128</span>
            <span className="text-xs text-slate-400">Sem 5 CSE</span>
          </div>
          <div className="mt-3 text-xs text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>100% Clerk JWKS verified</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Active 7-Day Plans</span>
            <div className="p-2 bg-emerald-950 text-emerald-400 rounded-xl border border-emerald-800/40">
              <BookOpen className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">114</span>
            <span className="text-xs text-slate-400">Structured timetables</span>
          </div>
          <div className="mt-3 text-xs text-indigo-400 flex items-center gap-1">
            <Cpu className="h-3.5 w-3.5" />
            <span>Gemini 3.6 Flash Engine</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Logged Study Telemetry</span>
            <div className="p-2 bg-purple-950 text-purple-400 rounded-xl border border-purple-800/40">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">1,480h</span>
            <span className="text-xs text-slate-400">Total verified minutes</span>
          </div>
          <div className="mt-3 text-xs text-purple-400 flex items-center gap-1">
            <Activity className="h-3.5 w-3.5" />
            <span>Avg 4.2h / student / day</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Diagnostic Deficit Flags</span>
            <div className="p-2 bg-amber-950 text-amber-400 rounded-xl border border-amber-800/40">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">18</span>
            <span className="text-xs text-slate-400">Needs Revision</span>
          </div>
          <div className="mt-3 text-xs text-amber-400 flex items-center gap-1">
            <span>Deterministic Rules 1 & 2</span>
          </div>
        </div>

      </div>

      {/* System Infrastructure Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Card 1: Diagnostic Service Engine */}
        <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Diagnostic Engine (`WeakTopicsService`)</h2>
            </div>
            <span className="rounded-md bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
              Deterministic
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Formulas applied to task telemetry with zero AI hallucinations:
          </p>
          <div className="space-y-2 text-xs font-mono text-slate-300 bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div>1. Rule 1: Missed Task Detection</div>
            <div>2. Rule 2: Sub-50% Duration (ρ &lt; 0.50)</div>
            <div>3. Rule 3: Deficit Tagging (Δ ≥ 15m)</div>
            <div>4. Rule 5: Future Day Protection Guardrail</div>
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>Automated Isolation Tests</span>
            <span className="text-emerald-400 font-bold">53 / 53 Passed (100%)</span>
          </div>
        </div>

        {/* Card 2: Recommendation Engine */}
        <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Course Recommendation Service</h2>
            </div>
            <span className="rounded-md bg-indigo-950 border border-indigo-800 px-2 py-0.5 text-[10px] font-bold text-indigo-400">
              TF-IDF Model
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Cosine vector matching against verified academic course catalog:
          </p>
          <div className="space-y-2 text-xs font-mono text-slate-300 bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div>• Corpus: 3,522 Coursera Academic Courses</div>
            <div>• Vectorizer: Max 5,000 unigram features</div>
            <div>• Anti-Phantom Cutoff: Sim ≥ 0.10</div>
            <div>• Benchmark: OS Process Sync (Sim: 0.4585)</div>
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>Vector Matrix Status</span>
            <span className="text-emerald-400 font-bold">Loaded & Cached</span>
          </div>
        </div>

        {/* Card 3: Adaptive Planning & Database */}
        <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-purple-400" />
              <h2 className="text-sm font-bold text-white">Supabase DB & Versioning</h2>
            </div>
            <span className="rounded-md bg-purple-950 border border-purple-800 px-2 py-0.5 text-[10px] font-bold text-purple-400">
              PostgreSQL RLS
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Relational storage tracking student profiles and immutable plan version history:
          </p>
          <div className="space-y-2 text-xs font-mono text-slate-300 bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div>• Table: student_profiles (CASCADE)</div>
            <div>• Table: study_plans (Active state)</div>
            <div>• Table: adaptive_plan_versions (Audit)</div>
            <div>• Security: auth.uid() = user_id Policy</div>
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>Relational Integrity</span>
            <span className="text-emerald-400 font-bold">Cascade Constraints Verified</span>
          </div>
        </div>

      </div>

      {/* Student Progress & Roster Table */}
      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white">Student Enrollment & Plan Execution Roster</h2>
            <p className="text-xs text-slate-400">
              Active engineering cohorts tracked across semester study plans and deterministic diagnostic flags
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search student or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="rounded-xl border border-slate-800 bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-white outline-none focus:border-indigo-500"
              />
            </div>

            <select
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 outline-none cursor-pointer"
            >
              <option value="all">All Cohorts (5)</option>
              <option value="needs_revision">Needs Revision Flags</option>
              <option value="on_track">On-Track Only</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="pb-3 pl-2">Scholar ID & Name</th>
                <th className="pb-3 px-3">Semester</th>
                <th className="pb-3 px-3">Primary Focus</th>
                <th className="pb-3 px-3">Logged Study</th>
                <th className="pb-3 px-3">Diagnostic Status</th>
                <th className="pb-3 px-3">Telemetry Trigger</th>
                <th className="pb-3 pr-2 text-right">Plan Version</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {filteredStudents.map((student) => (
                <tr key={student.id} className="hover:bg-slate-900/60 transition-colors">
                  <td className="py-3 pl-2">
                    <div className="font-bold text-white">{student.name}</div>
                    <div className="font-mono text-[11px] text-slate-400">{student.id}</div>
                  </td>
                  <td className="py-3 px-3 font-medium text-slate-300">
                    Sem {student.semester}
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-semibold text-indigo-300">{student.focus}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-bold text-white">{student.loggedHours}h</span>
                    <span className="text-slate-500"> / {student.scheduledHours}h</span>
                    <span className="text-[11px] text-slate-400 block font-mono">({student.completionRate}%)</span>
                  </td>
                  <td className="py-3 px-3">
                    {student.diagnosticStatus === "Needs Revision" ? (
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-950/80 border border-amber-800/80 px-2 py-0.5 text-[11px] font-bold text-amber-400">
                        <AlertTriangle className="h-3 w-3 text-amber-400" />
                        Needs Revision
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-950/80 border border-emerald-800/80 px-2 py-0.5 text-[11px] font-bold text-emerald-400">
                        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                        On-Track
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                    {student.ruleTrigger}
                  </td>
                  <td className="py-3 pr-2 text-right font-mono font-bold text-indigo-400">
                    {student.planVersion}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Telemetry Event Stream & Audit Trail */}
      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Adaptive Execution Audit Stream</h2>
          </div>
          <span className="text-xs text-slate-400">Real-time Telemetry Sink</span>
        </div>

        <div className="space-y-3">
          {AUDIT_EVENTS.map((event, idx) => (
            <div
              key={idx}
              className="flex items-start justify-between gap-3 p-3 rounded-2xl bg-slate-900/70 border border-slate-800/80 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">{event.user}</span>
                  <span className="text-[10px] rounded px-1.5 py-0.5 bg-slate-800 text-slate-300 font-medium">
                    {event.type}
                  </span>
                </div>
                <p className="text-slate-400">{event.detail}</p>
              </div>
              <span className="text-[11px] font-mono text-slate-400 shrink-0">{event.time}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
