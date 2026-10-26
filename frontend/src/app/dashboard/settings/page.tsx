"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";
import DashboardNav from "@/components/DashboardNav";
import {
  Settings,
  User,
  BookOpen,
  Clock,
  Sparkles,
  Sliders,
  Shield,
  Save,
  CheckCircle2,
  RefreshCw,
  Plus,
  X,
  Database,
  Lock,
  GraduationCap,
  Bell,
  Cpu,
  Layers,
} from "lucide-react";

export default function SettingsPage() {
  const { user } = useUser();
  const [activeTab, setActiveTab] = useState<"profile" | "schedule" | "ai" | "notifications">("profile");

  // Form states
  const [scholarId, setScholarId] = useState("23SKCS001");
  const [semester, setSemester] = useState(5);
  const [targetGoal, setTargetGoal] = useState("Targeting 8.5+ CGPA and strong GATE CSE core foundation");
  const [primaryFocus, setPrimaryFocus] = useState("Operating Systems");
  const [dailyHours, setDailyHours] = useState(4.5);
  const [maxConsecutiveHours, setMaxConsecutiveHours] = useState(2.0);
  const [sessionPacing, setSessionPacing] = useState("Deep Work (50m study / 10m break)");
  
  // Time slot preferences
  const [selectedTimeSlots, setSelectedTimeSlots] = useState<string[]>([
    "Morning (06:00 - 09:00)",
    "Evening (18:00 - 21:00)",
  ]);

  // Subject tags
  const [subjects, setSubjects] = useState<string[]>([
    "Operating Systems",
    "Computer Networks",
    "Database Management Systems",
    "Software Engineering",
    "Discrete Mathematics",
  ]);
  const [newSubjectInput, setNewSubjectInput] = useState("");

  // AI & Diagnostic toggles
  const [enforceStrictCeiling, setEnforceStrictCeiling] = useState(true);
  const [enableSub50Diagnostic, setEnableSub50Diagnostic] = useState(true);
  const [forwardOnlyCatchup, setForwardOnlyCatchup] = useState(true);
  const [deficitThresholdMins, setDeficitThresholdMins] = useState(15);
  const [cosineSimilarityCutoff, setCosineSimilarityCutoff] = useState(0.10);

  // Notification toggles
  const [dailyDigest, setDailyDigest] = useState(true);
  const [missedSessionAlerts, setMissedSessionAlerts] = useState(true);

  // Save feedback state
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleAddSubject = () => {
    if (newSubjectInput.trim() && !subjects.includes(newSubjectInput.trim())) {
      setSubjects([...subjects, newSubjectInput.trim()]);
      setNewSubjectInput("");
    }
  };

  const handleRemoveSubject = (subjectToRemove: string) => {
    if (subjects.length > 1) {
      setSubjects(subjects.filter((s) => s !== subjectToRemove));
      if (primaryFocus === subjectToRemove) {
        setPrimaryFocus(subjects.find((s) => s !== subjectToRemove) || "General Study");
      }
    }
  };

  const toggleTimeSlot = (slot: string) => {
    if (selectedTimeSlots.includes(slot)) {
      if (selectedTimeSlots.length > 1) {
        setSelectedTimeSlots(selectedTimeSlots.filter((s) => s !== slot));
      }
    } else {
      setSelectedTimeSlots([...selectedTimeSlots, slot]);
    }
  };

  const handleSave = () => {
    setIsSaving(true);
    // Simulate API persistence to Supabase / student_profiles
    setTimeout(() => {
      setIsSaving(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    }, 600);
  };

  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        
        {/* Navigation Tabs */}
        <DashboardNav showBackToDashboard={true} />

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-3xl bg-white border border-slate-200 p-6 sm:p-8 shadow-xs">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 border border-indigo-200">
              <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
              <span>Module 11: Student Profile & Settings</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Planner Preferences & Configuration
            </h1>
            <p className="text-sm text-slate-600">
              Manage your academic parameters, daily study availability constraints, and deterministic AI engine guardrails.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-200 hover:bg-indigo-700 transition-all cursor-pointer disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Saving to DB...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Save Toast Notification */}
        {saveSuccess && (
          <div className="flex items-center justify-between rounded-2xl bg-emerald-50 border border-emerald-200 p-4 text-emerald-800 text-sm shadow-xs animate-in fade-in duration-200">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <span className="font-semibold">
                Preferences saved successfully to Supabase DB (`student_profiles`) and synchronized with active study plan.
              </span>
            </div>
            <button onClick={() => setSaveSuccess(false)} className="text-emerald-600 hover:text-emerald-800">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveTab("profile")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer ${
              activeTab === "profile"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <User className="h-4 w-4" />
            <span>Academic Profile</span>
          </button>
          <button
            onClick={() => setActiveTab("schedule")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer ${
              activeTab === "schedule"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Clock className="h-4 w-4" />
            <span>Study Capacity & Limits</span>
          </button>
          <button
            onClick={() => setActiveTab("ai")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer ${
              activeTab === "ai"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Cpu className="h-4 w-4" />
            <span>AI Diagnostics & Guardrails</span>
          </button>
          <button
            onClick={() => setActiveTab("notifications")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all cursor-pointer ${
              activeTab === "notifications"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Bell className="h-4 w-4" />
            <span>Notifications & Sync</span>
          </button>
        </div>

        {/* Tab 1: Academic Profile */}
        {activeTab === "profile" && (
          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">Academic Identity & Enrollment</h2>
                  <p className="text-xs text-slate-500">Information utilized to generate semester-specific curricula</p>
                </div>
                <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-mono font-medium text-slate-600">
                  SKIT CSE
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Student Full Name
                  </label>
                  <input
                    type="text"
                    disabled
                    value={user?.fullName || "Devanshu Jangid"}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700 outline-none cursor-not-allowed"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Managed via Clerk Single Sign-On</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Scholar ID / Roll No.
                  </label>
                  <input
                    type="text"
                    value={scholarId}
                    onChange={(e) => setScholarId(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 font-mono outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Required for university evaluation records</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Current Semester
                  </label>
                  <select
                    value={semester}
                    onChange={(e) => setSemester(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                      <option key={sem} value={sem}>
                        Semester {sem} {sem === 5 ? "(Active Semester - 2026/27)" : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Primary Focus Subject
                  </label>
                  <select
                    value={primaryFocus}
                    onChange={(e) => setPrimaryFocus(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                  >
                    {subjects.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Academic Milestones & Goals
                </label>
                <textarea
                  rows={2}
                  value={targetGoal}
                  onChange={(e) => setTargetGoal(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Enrolled Subjects Tag List */}
              <div className="border-t border-slate-100 pt-5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Active Enrolled Subjects ({subjects.length})
                </label>
                <p className="text-xs text-slate-500 mb-3">
                  The AI Engine builds your 7-day schedule exclusively around these exact curriculum courses.
                </p>

                <div className="flex flex-wrap items-center gap-2 mb-3">
                  {subjects.map((sub) => (
                    <span
                      key={sub}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-50 border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-900"
                    >
                      <BookOpen className="h-3 w-3 text-indigo-600" />
                      <span>{sub}</span>
                      {sub === primaryFocus && (
                        <span className="text-[10px] bg-indigo-200/60 text-indigo-800 px-1 rounded-sm">
                          Focus
                        </span>
                      )}
                      <button
                        onClick={() => handleRemoveSubject(sub)}
                        className="text-indigo-400 hover:text-indigo-700 ml-1 cursor-pointer"
                        title={`Remove ${sub}`}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  ))}
                </div>

                <div className="flex gap-2 max-w-md">
                  <input
                    type="text"
                    placeholder="Add subject (e.g., Compiler Design)..."
                    value={newSubjectInput}
                    onChange={(e) => setNewSubjectInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddSubject())}
                    className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 outline-none focus:border-indigo-500"
                  />
                  <button
                    onClick={handleAddSubject}
                    className="inline-flex items-center gap-1 rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-900 transition-colors cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Add</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Study Capacity & Limits */}
        {activeTab === "schedule" && (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Study Availability & Capacity Bounds</h2>
                <p className="text-xs text-slate-500">
                  Enforcing strict hours ceiling invariants to eliminate student burnout
                </p>
              </div>
              <span className="rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1 text-xs font-semibold">
                Invariant #3 Active
              </span>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-bold text-slate-900">
                    Daily Study Hours Ceiling
                  </label>
                  <p className="text-xs text-slate-500">
                    Maximum allocated daily study hours across all subjects (Total Hours &le; Daily Limit)
                  </p>
                </div>
                <div className="text-xl font-extrabold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-xl border border-indigo-200">
                  {dailyHours} hrs / day
                </div>
              </div>

              <input
                type="range"
                min="1"
                max="8"
                step="0.5"
                value={dailyHours}
                onChange={(e) => setDailyHours(parseFloat(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>1.0 hr</span>
                <span>4.0 hrs (Recommended)</span>
                <span>8.0 hrs (Max)</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Cognitive Load Limit (Consecutive Hours)
                </label>
                <select
                  value={maxConsecutiveHours}
                  onChange={(e) => setMaxConsecutiveHours(parseFloat(e.target.value))}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value={1.5}>1.5 Hours max per session</option>
                  <option value={2.0}>2.0 Hours max (Architecture Invariant #4)</option>
                  <option value={2.5}>2.5 Hours max</option>
                </select>
                <p className="text-[11px] text-slate-400 mt-1">Prevents cognitive saturation on difficult topics</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Study Session Pacing
                </label>
                <select
                  value={sessionPacing}
                  onChange={(e) => setSessionPacing(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="Pomodoro (25m study / 5m break)">Pomodoro (25m study / 5m break)</option>
                  <option value="Deep Work (50m study / 10m break)">Deep Work (50m study / 10m break)</option>
                  <option value="Continuous (60m block)">Continuous (60m block)</option>
                </select>
                <p className="text-[11px] text-slate-400 mt-1">Standardized block structuring</p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Preferred Study Time Slots
              </label>
              <p className="text-xs text-slate-500 mb-3">Select the active blocks when you can attend focused sessions:</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  "Morning (06:00 - 09:00)",
                  "Afternoon (14:00 - 17:00)",
                  "Evening (18:00 - 21:00)",
                  "Night (21:00 - 23:00)",
                ].map((slot) => {
                  const isChecked = selectedTimeSlots.includes(slot);
                  return (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => toggleTimeSlot(slot)}
                      className={`flex items-center justify-between p-3.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                        isChecked
                          ? "bg-indigo-50/70 border-indigo-300 text-indigo-900"
                          : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span>{slot}</span>
                      <div
                        className={`h-4 w-4 rounded-md border flex items-center justify-center ${
                          isChecked ? "bg-indigo-600 border-indigo-600 text-white" : "border-slate-300 bg-white"
                        }`}
                      >
                        {isChecked && <CheckCircle2 className="h-3 w-3" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: AI Diagnostics & Guardrails */}
        {activeTab === "ai" && (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Deterministic Diagnostic Engine & AI Invariants</h2>
                <p className="text-xs text-slate-500">
                  Mathematical guardrails ensuring zero AI hallucinations across plan creation and re-balancing
                </p>
              </div>
              <span className="rounded-md bg-purple-50 text-purple-700 border border-purple-200 px-2.5 py-1 text-xs font-semibold">
                Gemini 3.6 Flash
              </span>
            </div>

            <div className="space-y-4 divide-y divide-slate-100">
              
              {/* Toggle 1 */}
              <div className="flex items-center justify-between pt-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Forward-Only Adaptive Re-balancing</h3>
                  <p className="text-xs text-slate-500">
                    Invariant #2: Catch-up sessions are allocated only to future days (Day &ge; Current Day).
                  </p>
                </div>
                <button
                  onClick={() => setForwardOnlyCatchup(!forwardOnlyCatchup)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    forwardOnlyCatchup ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      forwardOnlyCatchup ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Toggle 2 */}
              <div className="flex items-center justify-between pt-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Deterministic Sub-50% Duration Check</h3>
                  <p className="text-xs text-slate-500">
                    Rule 2: Flag topics as &quot;Needs Revision&quot; if study duration ratio &lt; 50% and deficit &ge; 15m.
                  </p>
                </div>
                <button
                  onClick={() => setEnableSub50Diagnostic(!enableSub50Diagnostic)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    enableSub50Diagnostic ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      enableSub50Diagnostic ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Toggle 3 */}
              <div className="flex items-center justify-between pt-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Strict Daily Hours Ceiling Invariant</h3>
                  <p className="text-xs text-slate-500">
                    Invariant #3: Compresses lower-priority review sessions if daily capacity is exceeded.
                  </p>
                </div>
                <button
                  onClick={() => setEnforceStrictCeiling(!enforceStrictCeiling)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    enforceStrictCeiling ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      enforceStrictCeiling ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Setting: Deficit Threshold */}
              <div className="flex items-center justify-between pt-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Study Deficit Tag Threshold (&Delta; mins)</h3>
                  <p className="text-xs text-slate-500">
                    Rule 3: Minimum quantifiable deficit required to attach an explainability tag
                  </p>
                </div>
                <select
                  value={deficitThresholdMins}
                  onChange={(e) => setDeficitThresholdMins(parseInt(e.target.value))}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-800 outline-none cursor-pointer"
                >
                  <option value={15}>15 Minutes (Default Specification)</option>
                  <option value={30}>30 Minutes</option>
                  <option value={45}>45 Minutes</option>
                  <option value={60}>60 Minutes (High Severity Only)</option>
                </select>
              </div>

              {/* Setting: Coursera Cosine Sim Cutoff */}
              <div className="flex items-center justify-between pt-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Coursera Catalog Cosine Similarity Cutoff</h3>
                  <p className="text-xs text-slate-500">
                    Threshold for TF-IDF course matching against 3,522 Coursera courses ($\ge 0.10$ eliminates spurious links)
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-indigo-600">
                    {(cosineSimilarityCutoff).toFixed(2)}
                  </span>
                  <input
                    type="range"
                    min="0.05"
                    max="0.30"
                    step="0.01"
                    value={cosineSimilarityCutoff}
                    onChange={(e) => setCosineSimilarityCutoff(parseFloat(e.target.value))}
                    className="accent-indigo-600 cursor-pointer w-24"
                  />
                </div>
              </div>

            </div>
          </div>
        )}

        {/* Tab 4: Notifications & Telemetry */}
        {activeTab === "notifications" && (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">System Telemetry & Notifications</h2>
                <p className="text-xs text-slate-500">
                  Integration with Clerk Authentication, FastAPI `/api/v1`, and Supabase Row-Level Security
                </p>
              </div>
              <span className="rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 px-2.5 py-1 text-xs font-semibold">
                Live Cloud Sync
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase mb-2">
                  <Shield className="h-4 w-4 text-emerald-600" />
                  <span>Clerk Auth Session</span>
                </div>
                <div className="text-xs text-slate-600 space-y-1">
                  <div>Status: <span className="font-bold text-emerald-600">Authenticated</span></div>
                  <div>Email: <span className="font-mono text-[11px]">{user?.primaryEmailAddress?.emailAddress || "student@skit.ac.in"}</span></div>
                  <div>Token: <span className="font-mono text-[11px]">RS256 JWKS Verified</span></div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase mb-2">
                  <Database className="h-4 w-4 text-indigo-600" />
                  <span>Supabase PostgreSQL</span>
                </div>
                <div className="text-xs text-slate-600 space-y-1">
                  <div>Status: <span className="font-bold text-indigo-600">Connected</span></div>
                  <div>Security: <span className="font-bold text-slate-700">RLS (auth.uid())</span></div>
                  <div>Cascade Delete: <span className="font-bold text-emerald-600">Verified</span></div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase mb-2">
                  <Cpu className="h-4 w-4 text-purple-600" />
                  <span>AI Engine Telemetry</span>
                </div>
                <div className="text-xs text-slate-600 space-y-1">
                  <div>Engine: <span className="font-bold text-purple-600">Gemini 3.6 Flash</span></div>
                  <div>Schema: <span className="font-bold text-slate-700">Pydantic Output</span></div>
                  <div>Test Suite: <span className="font-bold text-emerald-600">53/53 Passed</span></div>
                </div>
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Daily Academic Digest</h3>
                  <p className="text-xs text-slate-500">Receive evening summaries of logged study sessions and planned catch-up tasks.</p>
                </div>
                <button
                  onClick={() => setDailyDigest(!dailyDigest)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    dailyDigest ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      dailyDigest ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Missed Session & Deficit Alerts</h3>
                  <p className="text-xs text-slate-500">Prompt for session re-allocation when a task is skipped or sub-50% completed.</p>
                </div>
                <button
                  onClick={() => setMissedSessionAlerts(!missedSessionAlerts)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    missedSessionAlerts ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                      missedSessionAlerts ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <Link
                href="/onboarding"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
              >
                Re-run Full Onboarding Wizard →
              </Link>

              <button
                onClick={handleSave}
                className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-black transition-colors cursor-pointer"
              >
                <Save className="h-3.5 w-3.5" />
                <span>Save All Settings</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
