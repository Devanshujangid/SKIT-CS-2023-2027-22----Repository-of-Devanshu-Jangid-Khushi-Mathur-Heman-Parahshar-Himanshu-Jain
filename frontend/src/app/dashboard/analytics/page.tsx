"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";
import DashboardNav from "@/components/DashboardNav";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Award,
  Calendar,
  Filter,
  Download,
  BookOpen,
  Sparkles,
  ArrowRight,
  Brain,
  ShieldAlert,
  BarChart2,
  Zap,
} from "lucide-react";

// Weekly study hours data (Scheduled vs Actual)
const WEEKLY_HOURS_DATA = [
  { day: "Mon", scheduled: 4.5, actual: 4.0, deficit: 0.5, completion: 89 },
  { day: "Tue", scheduled: 5.0, actual: 4.8, deficit: 0.2, completion: 96 },
  { day: "Wed", scheduled: 4.5, actual: 2.0, deficit: 2.5, completion: 44 }, // Sub-50% trigger!
  { day: "Thu", scheduled: 4.0, actual: 4.0, deficit: 0.0, completion: 100 },
  { day: "Fri", scheduled: 5.5, actual: 5.0, deficit: 0.5, completion: 91 },
  { day: "Sat", scheduled: 6.0, actual: 6.5, deficit: 0.0, completion: 108 }, // Catch-up session
  { day: "Sun", scheduled: 5.0, actual: 4.5, deficit: 0.5, completion: 90 },
];

// Subject distribution
const SUBJECT_DISTRIBUTION = [
  { name: "Operating Systems", hours: 10.5, color: "#6366F1", mastery: 88 },
  { name: "Computer Networks", hours: 8.0, color: "#06B6D4", mastery: 79 },
  { name: "Database Systems", hours: 7.5, color: "#10B981", mastery: 92 },
  { name: "Software Engineering", hours: 5.5, color: "#F59E0B", mastery: 85 },
  { name: "Discrete Mathematics", hours: 4.0, color: "#8B5CF6", mastery: 72 },
];

// Weekly trend data across weeks (Deficit vs Recovered)
const HISTORICAL_TRENDS = [
  { week: "Wk 1", planned: 28, actual: 26, deficitMins: 120, recoveredMins: 90 },
  { week: "Wk 2", planned: 30, actual: 29, deficitMins: 60, recoveredMins: 60 },
  { week: "Wk 3", planned: 32, actual: 28, deficitMins: 240, recoveredMins: 180 },
  { week: "Wk 4", planned: 30, actual: 30, deficitMins: 0, recoveredMins: 0 },
  { week: "Wk 5", planned: 34, actual: 32, deficitMins: 120, recoveredMins: 120 },
  { week: "Wk 6", planned: 35, actual: 31, deficitMins: 240, recoveredMins: 210 },
  { week: "Wk 7", planned: 34, actual: 33, deficitMins: 60, recoveredMins: 60 },
  { week: "Wk 8 (Current)", planned: 34.5, actual: 30.8, deficitMins: 220, recoveredMins: 180 },
];

// Radar chart for subject mastery vs target
const MASTERY_RADAR_DATA = [
  { subject: "Operating Systems", current: 88, target: 95, fullMark: 100 },
  { subject: "Computer Networks", current: 79, target: 90, fullMark: 100 },
  { subject: "DBMS & SQL", current: 92, target: 90, fullMark: 100 },
  { subject: "Software Eng", current: 85, target: 85, fullMark: 100 },
  { subject: "Discrete Math", current: 72, target: 85, fullMark: 100 },
];

// Telemetry task breakdown
const DIAGNOSTIC_TOPICS_BREAKDOWN = [
  {
    subject: "Operating Systems",
    topic: "Process Synchronization & Semaphores",
    plannedMins: 180,
    actualMins: 75,
    ratio: 0.41,
    status: "Needs Revision",
    ruleTrigger: "Rule 2: Sub-50% Duration (41%)",
    severity: "high",
    recommendedAction: "Adaptive Catch-up session scheduled",
  },
  {
    subject: "Discrete Mathematics",
    topic: "Graph Theory & Trees",
    plannedMins: 120,
    actualMins: 0,
    ratio: 0.0,
    status: "Needs Revision",
    ruleTrigger: "Rule 1: Missed Task (Session skipped)",
    severity: "high",
    recommendedAction: "TF-IDF Coursera Course linked",
  },
  {
    subject: "Database Systems",
    topic: "B+ Tree Indexing & Query Optimization",
    plannedMins: 150,
    actualMins: 140,
    ratio: 0.93,
    status: "On-Track",
    ruleTrigger: "All criteria satisfied",
    severity: "normal",
    recommendedAction: "Proceed to Practice Problems",
  },
  {
    subject: "Computer Networks",
    topic: "TCP Flow & Congestion Control",
    plannedMins: 160,
    actualMins: 155,
    ratio: 0.96,
    status: "On-Track",
    ruleTrigger: "All criteria satisfied",
    severity: "normal",
    recommendedAction: "Lab Simulation Completed",
  },
  {
    subject: "Software Engineering",
    topic: "Agile Estimation & CI/CD Pipelines",
    plannedMins: 120,
    actualMins: 110,
    ratio: 0.91,
    status: "On-Track",
    ruleTrigger: "All criteria satisfied",
    severity: "normal",
    recommendedAction: "Weekly Review Passed",
  },
];

export default function AnalyticsPage() {
  const { user } = useUser();
  const [isMounted, setIsMounted] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState<"7days" | "14days" | "semester">("7days");
  const [selectedSubjectFilter, setSelectedSubjectFilter] = useState<string>("All");

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const totalScheduledHours = 34.5;
  const totalActualHours = 30.8;
  const adherenceRate = Math.round((totalActualHours / totalScheduledHours) * 100);
  const completedTasksCount = 28;
  const totalTasksCount = 32;
  const completionPercentage = Math.round((completedTasksCount / totalTasksCount) * 100);

  const filteredTopics = selectedSubjectFilter === "All"
    ? DIAGNOSTIC_TOPICS_BREAKDOWN
    : DIAGNOSTIC_TOPICS_BREAKDOWN.filter((t) => t.subject === selectedSubjectFilter);

  return (
    <main className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        
        {/* Navigation Tabs */}
        <DashboardNav showBackToDashboard={true} />

        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 sm:p-8 text-white shadow-xl">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-300 border border-indigo-400/30">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              <span>Module 8: Academic Progress & Telemetry Analytics</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Study Analytics & Performance Dashboard
            </h1>
            <p className="max-w-2xl text-sm sm:text-base text-slate-300">
              Deterministic diagnostic tracking of actual study minutes, deficit recovery velocity,
              and subject mastery adherence for student {user?.firstName ? `${user.firstName}` : "Devanshu"}.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex rounded-xl bg-white/10 p-1 border border-white/10">
              <button
                onClick={() => setSelectedTimeframe("7days")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  selectedTimeframe === "7days"
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                7-Day Cycle
              </button>
              <button
                onClick={() => setSelectedTimeframe("14days")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  selectedTimeframe === "14days"
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                14 Days
              </button>
              <button
                onClick={() => setSelectedTimeframe("semester")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  selectedTimeframe === "semester"
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                Full Semester
              </button>
            </div>

            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 px-3.5 py-2 text-xs font-semibold text-white transition-colors cursor-pointer"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export Report</span>
            </button>
          </div>
        </div>

        {/* Top 4 KPI Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Study Velocity</span>
              <div className="p-2 bg-indigo-50 rounded-xl text-indigo-600">
                <Clock className="h-5 w-5" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-slate-900">{totalActualHours}h</span>
              <span className="text-xs font-medium text-slate-500">/ {totalScheduledHours}h scheduled</span>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>{adherenceRate}% adherence target</span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Session Completion</span>
              <div className="p-2 bg-emerald-50 rounded-xl text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-slate-900">{completedTasksCount}</span>
              <span className="text-xs font-medium text-slate-500">/ {totalTasksCount} sessions</span>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
              <span>{completionPercentage}% completed on schedule</span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Diagnostic Deficits</span>
              <div className="p-2 bg-amber-50 rounded-xl text-amber-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-amber-600">2 Flags</span>
              <span className="text-xs font-medium text-slate-500">Needs Revision</span>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-amber-700">
              <span>Deterministic Rule 1 & 2 triggers</span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider">Cognitive Load Factor</span>
              <div className="p-2 bg-purple-50 rounded-xl text-purple-600">
                <Brain className="h-5 w-5" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-slate-900">Optimal</span>
              <span className="text-xs font-medium text-slate-500">≤ 2.0h max block</span>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-purple-600">
              <Zap className="h-3.5 w-3.5" />
              <span>Invariant #4 fully adhered</span>
            </div>
          </div>
        </div>

        {/* Primary Visualizations Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Chart 1: Scheduled vs Actual Hours (BarChart) */}
          <div className="lg:col-span-2 rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Daily Study Hours: Scheduled vs Actual</h2>
                <p className="text-xs text-slate-500">
                  Telemetry comparisons across the 7-day cycle with deterministic deficit markers
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
                <div className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-sm bg-indigo-600"></span>
                  <span>Scheduled</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-sm bg-emerald-500"></span>
                  <span>Actual Logged</span>
                </div>
              </div>
            </div>

            <div className="h-72 w-full">
              {isMounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={WEEKLY_HOURS_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 12 }} stroke="#CBD5E1" />
                    <YAxis tick={{ fill: "#64748B", fontSize: 12 }} stroke="#CBD5E1" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0F172A",
                        borderRadius: "12px",
                        border: "none",
                        color: "#FFFFFF",
                        fontSize: "12px",
                        boxShadow: "0 10px 25px -5px rgba(0,0,0,0.3)",
                      }}
                      formatter={(val: any, name: any) => [`${val} hours`, name === "scheduled" ? "Scheduled" : "Actual Logged"]}
                    />
                    <Bar dataKey="scheduled" fill="#818CF8" radius={[6, 6, 0, 0]} barSize={22} />
                    <Bar dataKey="actual" fill="#10B981" radius={[6, 6, 0, 0]} barSize={22} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                  Loading visual telemetry...
                </div>
              )}
            </div>
            
            <div className="mt-4 rounded-xl bg-slate-50 p-3 flex items-center justify-between text-xs text-slate-600 border border-slate-100">
              <span>Notice: <strong>Wednesday</strong> experienced a sub-50% study deficit (2.0h / 4.5h), triggering deterministic Rule 2.</span>
              <Link href="/dashboard" className="text-indigo-600 font-semibold hover:underline inline-flex items-center gap-1">
                View in Schedule <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>

          {/* Chart 2: Subject Time Share (PieChart) */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs flex flex-col justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Subject Distribution</h2>
              <p className="text-xs text-slate-500 mb-4">
                Allocation of 34.5 weekly hours across curriculum topics
              </p>

              <div className="h-56 w-full flex items-center justify-center">
                {isMounted ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={SUBJECT_DISTRIBUTION}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                        dataKey="hours"
                      >
                        {SUBJECT_DISTRIBUTION.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: any) => [`${val} hrs`, "Planned Allocation"]}
                        contentStyle={{
                          backgroundColor: "#0F172A",
                          borderRadius: "10px",
                          border: "none",
                          color: "#FFF",
                          fontSize: "12px",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                    Loading distribution...
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2 mt-2">
              {SUBJECT_DISTRIBUTION.map((sub) => (
                <div key={sub.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: sub.color }}></span>
                    <span className="font-medium text-slate-700">{sub.name}</span>
                  </div>
                  <span className="font-bold text-slate-900">{sub.hours}h</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Secondary Charts: Mastery Radar & Deficit Recovery Velocity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Chart 3: Historical Deficit Recovery (AreaChart) */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Adaptive Rebalance Velocity (Weeks 1–8)</h2>
                <p className="text-xs text-slate-500">
                  Deficit minutes detected vs recovered via forward-only adaptive re-balancing
                </p>
              </div>
              <div className="p-2 bg-indigo-50 rounded-xl text-indigo-600">
                <BarChart2 className="h-4 w-4" />
              </div>
            </div>

            <div className="h-64 w-full">
              {isMounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={HISTORICAL_TRENDS} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="deficitGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="recoveredGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                    <XAxis dataKey="week" tick={{ fill: "#64748B", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#64748B", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0F172A",
                        borderRadius: "10px",
                        border: "none",
                        color: "#FFF",
                        fontSize: "12px",
                      }}
                      formatter={(val: any, name: any) => [
                        `${val} mins`,
                        name === "deficitMins" ? "Study Deficit" : "Recovered Catch-up",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="deficitMins"
                      stroke="#EF4444"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#deficitGradient)"
                    />
                    <Area
                      type="monotone"
                      dataKey="recoveredMins"
                      stroke="#6366F1"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#recoveredGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                  Loading recovery velocity...
                </div>
              )}
            </div>

            <div className="mt-3 flex items-center justify-around border-t border-slate-100 pt-3 text-xs text-slate-600">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500"></span>
                <span>Cumulative Deficits: <strong>1,080 mins</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-indigo-600"></span>
                <span>Adaptive Recoveries: <strong>900 mins (83.3%)</strong></span>
              </div>
            </div>
          </div>

          {/* Chart 4: Subject Mastery Radar */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Curriculum Mastery vs Target</h2>
                <p className="text-xs text-slate-500">
                  Student competency score vs semester target score (SKIT CSE Benchmark)
                </p>
              </div>
              <div className="p-2 bg-purple-50 rounded-xl text-purple-600">
                <Award className="h-4 w-4" />
              </div>
            </div>

            <div className="h-64 w-full">
              {isMounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={MASTERY_RADAR_DATA}>
                    <PolarGrid stroke="#E2E8F0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: "#475569", fontSize: 11 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#CBD5E1" />
                    <Radar
                      name="Current Mastery"
                      dataKey="current"
                      stroke="#6366F1"
                      fill="#6366F1"
                      fillOpacity={0.4}
                    />
                    <Radar
                      name="Target Benchmark"
                      dataKey="target"
                      stroke="#10B981"
                      fill="#10B981"
                      fillOpacity={0.2}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0F172A",
                        borderRadius: "10px",
                        border: "none",
                        color: "#FFF",
                        fontSize: "12px",
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                  Loading radar data...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Deterministic Diagnostic Telemetry Table */}
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-indigo-600" />
                <h2 className="text-lg font-bold text-slate-900">Deterministic Diagnostic Telemetry</h2>
              </div>
              <p className="text-xs text-slate-500">
                Telemetry rules evaluating study duration ratio &rho; &lt; 0.50 and missed task invariants (Zero-Hallucination)
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Filter className="h-3.5 w-3.5 text-slate-400" />
              <select
                value={selectedSubjectFilter}
                onChange={(e) => setSelectedSubjectFilter(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <option value="All">All Subjects</option>
                <option value="Operating Systems">Operating Systems</option>
                <option value="Computer Networks">Computer Networks</option>
                <option value="Database Systems">Database Systems</option>
                <option value="Software Engineering">Software Engineering</option>
                <option value="Discrete Mathematics">Discrete Mathematics</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-3 pl-2">Subject & Topic</th>
                  <th className="pb-3 px-3">Planned vs Actual</th>
                  <th className="pb-3 px-3">Duration Ratio (ρ)</th>
                  <th className="pb-3 px-3">Diagnostic Status</th>
                  <th className="pb-3 px-3">Mathematical Trigger</th>
                  <th className="pb-3 pr-2 text-right">Adaptive Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {filteredTopics.map((topic, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 pl-2 font-medium">
                      <div className="text-slate-900 font-semibold">{topic.topic}</div>
                      <div className="text-[11px] text-slate-500">{topic.subject}</div>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="font-semibold text-slate-900">{topic.actualMins}m</span>
                      <span className="text-slate-400"> / {topic.plannedMins}m</span>
                    </td>
                    <td className="py-3.5 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              topic.ratio < 0.5 ? "bg-red-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${Math.min(100, topic.ratio * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-slate-600">
                          {Math.round(topic.ratio * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-3">
                      {topic.status === "Needs Revision" ? (
                        <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 border border-amber-200 px-2.5 py-1 text-[11px] font-bold text-amber-700">
                          <AlertTriangle className="h-3 w-3 text-amber-500" />
                          Needs Revision
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
                          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                          On-Track
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="text-slate-600 font-mono text-[11px]">
                        {topic.ruleTrigger}
                      </span>
                    </td>
                    <td className="py-3.5 pr-2 text-right">
                      <span className="text-indigo-600 font-medium text-xs">
                        {topic.recommendedAction}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 50% Checkpoint Invariant Guardrail Banner */}
        <div className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-white p-5 text-xs text-indigo-950 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 text-white rounded-xl">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <p className="font-bold text-sm text-slate-900">Deterministic Architectural Grounding</p>
              <p className="text-slate-600">
                All visual charts and telemetry above map 1:1 to the SKIT CSE 50% Checkpoint Architecture Specification.
                Zero probabilistic LLM hallucination permitted in diagnostic flags.
              </p>
            </div>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors shrink-0"
          >
            <span>Return to Timetable</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

      </div>
    </main>
  );
}
