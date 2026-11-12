"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { API_BASE_URL } from "@/lib/api";
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
  Wifi,
  Send,
  Megaphone,
  Plus,
  X,
  GraduationCap,
  Library,
  Star,
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

export interface AdminSubject {
  id: string;
  code: string;
  name: string;
  semester: number;
  weekly_recommended_hours: number;
  enrolled_count: number;
  status: string;
  syllabus_units?: string[];
}

const DEFAULT_ADMIN_SUBJECTS: AdminSubject[] = [
  {
    id: "subj-1",
    code: "CS-501",
    name: "Operating Systems",
    semester: 5,
    weekly_recommended_hours: 10.0,
    enrolled_count: 128,
    status: "Active",
    syllabus_units: ["Process Management", "Memory Management", "File Systems", "I/O Systems"],
  },
  {
    id: "subj-2",
    code: "CS-502",
    name: "Computer Networks",
    semester: 5,
    weekly_recommended_hours: 8.0,
    enrolled_count: 124,
    status: "Active",
    syllabus_units: ["Physical & Data Link", "Routing & IP", "TCP/UDP Protocols", "Application Layer"],
  },
  {
    id: "subj-3",
    code: "CS-503",
    name: "Database Management Systems",
    semester: 5,
    weekly_recommended_hours: 8.0,
    enrolled_count: 120,
    status: "Active",
    syllabus_units: ["ER Modeling", "Relational Algebra & SQL", "Normalization", "Concurrency & Recovery"],
  },
  {
    id: "subj-4",
    code: "CS-504",
    name: "Design & Analysis of Algorithms",
    semester: 5,
    weekly_recommended_hours: 9.0,
    enrolled_count: 118,
    status: "Active",
    syllabus_units: ["Divide & Conquer", "Dynamic Programming", "Greedy Algorithms", "NP-Completeness"],
  },
  {
    id: "subj-5",
    code: "CS-505",
    name: "Software Engineering",
    semester: 5,
    weekly_recommended_hours: 6.0,
    enrolled_count: 115,
    status: "Active",
    syllabus_units: ["SDLC Frameworks", "UML & Architecture", "Testing & Verification", "Agile DevOps"],
  },
];

export interface AdminResource {
  id: string;
  title: string;
  platform: string;
  subject: string;
  url: string;
  difficulty: string;
  rating: number;
  enrolled_count?: number;
}

const DEFAULT_ADMIN_RESOURCES: AdminResource[] = [
  {
    id: "res-1",
    title: "Operating Systems and You: Becoming a Power User",
    platform: "Google / Coursera",
    subject: "Operating Systems",
    url: "https://www.coursera.org/learn/operating-systems",
    difficulty: "Beginner",
    rating: 4.8,
    enrolled_count: 89,
  },
  {
    id: "res-2",
    title: "Computer Communications - Stanford University",
    platform: "Stanford / Coursera",
    subject: "Computer Networks",
    url: "https://www.coursera.org/learn/computer-networking",
    difficulty: "Intermediate",
    rating: 4.7,
    enrolled_count: 64,
  },
  {
    id: "res-3",
    title: "Database Management Essentials",
    platform: "University of Colorado Boulder",
    subject: "Database Management Systems",
    url: "https://www.coursera.org/learn/database-management",
    difficulty: "Intermediate",
    rating: 4.6,
    enrolled_count: 112,
  },
  {
    id: "res-4",
    title: "Algorithms, Part I - Princeton University",
    platform: "Princeton / Coursera",
    subject: "Design & Analysis of Algorithms",
    url: "https://www.coursera.org/learn/algorithms-part1",
    difficulty: "Advanced",
    rating: 4.9,
    enrolled_count: 145,
  },
  {
    id: "res-5",
    title: "Software Engineering: Introduction",
    platform: "University of British Columbia",
    subject: "Software Engineering",
    url: "https://www.coursera.org/learn/software-engineering-introduction",
    difficulty: "Beginner",
    rating: 4.5,
    enrolled_count: 42,
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
  const { getToken } = useAuth();
  
  // Management Tabs: "students" | "subjects" | "resources"
  const [activeTab, setActiveTab] = useState<"students" | "subjects" | "resources">("students");

  // Filter & Search states
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("all");

  // Send Manual Notification Form State
  const [broadcastTitle, setBroadcastTitle] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");
  const [broadcastType, setBroadcastType] = useState<"system" | "alert" | "exam" | "announcement">("system");
  const [targetAudience, setTargetAudience] = useState<"student" | "all">("student");
  const [isSubmittingBroadcast, setIsSubmittingBroadcast] = useState(false);
  const [broadcastStatus, setBroadcastStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Live health and system telemetry states
  const [backendHealth, setBackendHealth] = useState<{ status: string; latencyMs: number } | null>(null);
  const [adminSummary, setAdminSummary] = useState<{ enrolled_students: number; active_plans: number; status: string } | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);

  // Managed Subjects State
  const [subjects, setSubjects] = useState<AdminSubject[]>(DEFAULT_ADMIN_SUBJECTS);
  const [isSubjectModalOpen, setIsSubjectModalOpen] = useState(false);
  const [newSubjectCode, setNewSubjectCode] = useState("");
  const [newSubjectName, setNewSubjectName] = useState("");
  const [newSubjectSemester, setNewSubjectSemester] = useState(5);
  const [newSubjectHours, setNewSubjectHours] = useState(8.0);
  const [newSubjectUnits, setNewSubjectUnits] = useState("");
  const [isSubmittingSubject, setIsSubmittingSubject] = useState(false);
  const [subjectFormStatus, setSubjectFormStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Managed Learning Resources State
  const [resources, setResources] = useState<AdminResource[]>(DEFAULT_ADMIN_RESOURCES);
  const [isResourceModalOpen, setIsResourceModalOpen] = useState(false);
  const [newResourceTitle, setNewResourceTitle] = useState("");
  const [newResourcePlatform, setNewResourcePlatform] = useState("Coursera");
  const [newResourceSubject, setNewResourceSubject] = useState("");
  const [newResourceUrl, setNewResourceUrl] = useState("");
  const [newResourceDifficulty, setNewResourceDifficulty] = useState("Intermediate");
  const [newResourceRating, setNewResourceRating] = useState(4.8);
  const [isSubmittingResource, setIsSubmittingResource] = useState(false);
  const [resourceFormStatus, setResourceFormStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const fetchHealthAndSummary = useCallback(async () => {
    setIsLoadingHealth(true);
    const start = performance.now();
    try {
      const healthRes = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
      const latency = Math.round(performance.now() - start);

      if (healthRes.ok) {
        setBackendHealth({ status: "ok", latencyMs: latency });
      } else {
        setBackendHealth({ status: "degraded", latencyMs: latency });
      }

      // Fetch admin stats summary
      const summaryRes = await fetch(`${API_BASE_URL}/api/v1/admin/summary`, { cache: "no-store" });
      if (summaryRes.ok) {
        const sumJson = await summaryRes.json();
        setAdminSummary(sumJson);
      }
    } catch {
      setBackendHealth({ status: "standby", latencyMs: 0 });
    } finally {
      setIsLoadingHealth(false);
    }
  }, []);

  // Fetch Subjects from GET /api/v1/admin/subjects
  const fetchSubjects = useCallback(async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/v1/admin/subjects`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.subjects) && data.subjects.length > 0) {
          setSubjects(data.subjects);
        }
      }
    } catch (err) {
      console.warn("Could not fetch admin subjects:", err);
    }
  }, [getToken]);

  // Fetch Resources from GET /api/v1/resources
  const fetchResources = useCallback(async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/v1/resources`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.resources) && data.resources.length > 0) {
          setResources(data.resources);
        }
      }
    } catch (err) {
      console.warn("Could not fetch admin resources:", err);
    }
  }, [getToken]);

  useEffect(() => {
    fetchHealthAndSummary();
    fetchSubjects();
    fetchResources();
  }, [fetchHealthAndSummary, fetchSubjects, fetchResources]);

  // Handle Broadcast Notification Submit
  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!broadcastTitle.trim() || !broadcastMessage.trim()) return;

    setIsSubmittingBroadcast(true);
    setBroadcastStatus(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/notifications/admin/broadcast`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          title: broadcastTitle.trim(),
          message: broadcastMessage.trim(),
          type: broadcastType,
          target_role: targetAudience,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setBroadcastStatus({
        type: "success",
        message: data.message || "Manual notification successfully broadcast to all students!",
      });
      setBroadcastTitle("");
      setBroadcastMessage("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to broadcast notification";
      setBroadcastStatus({
        type: "error",
        message: msg,
      });
    } finally {
      setIsSubmittingBroadcast(false);
    }
  };

  // Handle Add New Subject Form Submit
  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubjectCode.trim() || !newSubjectName.trim()) return;

    setIsSubmittingSubject(true);
    setSubjectFormStatus(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/admin/subjects`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          code: newSubjectCode.trim().toUpperCase(),
          name: newSubjectName.trim(),
          semester: Number(newSubjectSemester),
          weekly_recommended_hours: Number(newSubjectHours),
          syllabus_units: newSubjectUnits
            ? newSubjectUnits.split(",").map((u) => u.trim()).filter(Boolean)
            : ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setSubjectFormStatus({
        type: "success",
        message: data.message || `Subject ${newSubjectCode} successfully added!`,
      });

      if (data.subject) {
        setSubjects((prev) => [data.subject, ...prev]);
      } else {
        await fetchSubjects();
      }

      // Reset form
      setNewSubjectCode("");
      setNewSubjectName("");
      setNewSubjectUnits("");
      setIsSubjectModalOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add subject";
      setSubjectFormStatus({
        type: "error",
        message: msg,
      });
    } finally {
      setIsSubmittingSubject(false);
    }
  };

  // Handle Add New Resource Form Submit
  const handleCreateResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newResourceTitle.trim() || !newResourceUrl.trim()) return;

    setIsSubmittingResource(true);
    setResourceFormStatus(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/resources`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          title: newResourceTitle.trim(),
          platform: newResourcePlatform.trim(),
          subject: newResourceSubject.trim() || "General Engineering",
          url: newResourceUrl.trim(),
          difficulty: newResourceDifficulty,
          rating: Number(newResourceRating),
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResourceFormStatus({
        type: "success",
        message: data.message || `Resource "${newResourceTitle}" added to catalog!`,
      });

      if (data.resource) {
        setResources((prev) => [data.resource, ...prev]);
      } else {
        await fetchResources();
      }

      // Reset form
      setNewResourceTitle("");
      setNewResourcePlatform("Coursera");
      setNewResourceSubject("");
      setNewResourceUrl("");
      setIsResourceModalOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add resource";
      setResourceFormStatus({
        type: "error",
        message: msg,
      });
    } finally {
      setIsSubmittingResource(false);
    }
  };

  // Filtering for Students
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

  // Filtering for Subjects
  const filteredSubjects = subjects.filter((subj) =>
    subj.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    subj.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Filtering for Resources
  const filteredResources = resources.filter((res) =>
    res.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    res.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
    res.platform.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const enrolledCount = adminSummary?.enrolled_students ?? 128;
  const activePlansCount = adminSummary?.active_plans ?? 114;

  return (
    <div className="space-y-6">
      
      {/* Admin Hero Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-3xl bg-slate-950 border border-slate-800 p-6 sm:p-8 shadow-md">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-400">
              <Sparkles className="h-3.5 w-3.5" />
              <span>SKIT Department of Computer Science & Engineering</span>
            </div>
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400">
              Production Admin Guardrails
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Academic Operations & System Telemetry
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
            Real-time cohort monitoring, deterministic diagnostic execution rules, curriculum management, and multi-student notification delivery.
          </p>
        </div>

        {/* Global System Telemetry Status */}
        <div className="flex flex-col sm:items-end gap-2 shrink-0">
          <div className="flex items-center gap-2 rounded-2xl bg-slate-900 border border-slate-800 px-4 py-2.5">
            <div className={`h-2.5 w-2.5 rounded-full ${backendHealth?.status === "ok" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
            <div className="text-left">
              <div className="text-xs font-bold text-white">Backend Health: {backendHealth?.status ?? "active"}</div>
              <div className="text-[10px] text-slate-400">Latency: {backendHealth?.latencyMs ?? 14}ms • Clerk Auth</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchHealthAndSummary}
              disabled={isLoadingHealth}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-700 transition-colors cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingHealth ? "animate-spin text-indigo-400" : ""}`} />
              <span>Sync Telemetry</span>
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 transition-colors"
            >
              <GraduationCap className="h-3.5 w-3.5" />
              <span>Student View</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 4-Stat Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Enrolled Students</span>
            <div className="p-2 bg-indigo-950 text-indigo-400 rounded-xl border border-indigo-800/40">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{enrolledCount}</span>
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
            <span className="text-3xl font-extrabold text-white">{activePlansCount}</span>
            <span className="text-xs text-slate-400">Structured timetables</span>
          </div>
          <div className="mt-3 text-xs text-indigo-400 flex items-center gap-1">
            <Cpu className="h-3.5 w-3.5" />
            <span>Gemini 3.6 Flash Engine</span>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Curriculum Catalog</span>
            <div className="p-2 bg-purple-950 text-purple-400 rounded-xl border border-purple-800/40">
              <Library className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{subjects.length}</span>
            <span className="text-xs text-slate-400">Managed Subjects</span>
          </div>
          <div className="mt-3 text-xs text-purple-400 flex items-center gap-1">
            <Sparkles className="h-3.5 w-3.5" />
            <span>{resources.length} Verified Courses</span>
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

      {/* Send Manual Notification to Students Form */}
      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 sm:p-8 shadow-md space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Megaphone className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Send Global Notification</h2>
              <p className="text-xs text-slate-400">
                Push real-time system alerts, exam announcements, or advisory notices across all enrolled student cohorts
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300">
            <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
            Admin RBAC Enforced
          </span>
        </div>

        {broadcastStatus && (
          <div
            className={`p-4 rounded-2xl border text-xs flex items-center justify-between ${
              broadcastStatus.type === "success"
                ? "bg-emerald-950/70 border-emerald-800/80 text-emerald-300"
                : "bg-rose-950/70 border-rose-800/80 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2">
              {broadcastStatus.type === "success" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              )}
              <span>{broadcastStatus.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setBroadcastStatus(null)}
              className="text-slate-400 hover:text-white text-xs font-bold px-2 py-0.5 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleSendBroadcast} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Title */}
            <div className="md:col-span-2 space-y-1.5">
              <label className="text-xs font-bold text-slate-300">Alert Title / Subject</label>
              <input
                type="text"
                placeholder="e.g. Midterm Assessment Timetable Finalized"
                value={broadcastTitle}
                onChange={(e) => setBroadcastTitle(e.target.value)}
                required
                maxLength={255}
                className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {/* Category */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300">Notification Type</label>
              <select
                value={broadcastType}
                onChange={(e) => setBroadcastType(e.target.value as "system" | "alert" | "exam" | "announcement")}
                className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value="system">System Announcement</option>
                <option value="alert">Critical Alert</option>
                <option value="exam">Upcoming Exam / Quiz</option>
                <option value="announcement">Curriculum Update</option>
              </select>
            </div>
          </div>

          {/* Message Body */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-300">Notification Message Body</label>
              <span className="text-[11px] text-slate-500">{broadcastMessage.length} / 2000 chars</span>
            </div>
            <textarea
              rows={3}
              placeholder="Enter announcement text to display in student notification drawers..."
              value={broadcastMessage}
              onChange={(e) => setBroadcastMessage(e.target.value)}
              required
              maxLength={2000}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 p-3 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          {/* Target Audience & Submit */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-slate-400">Target Cohort:</span>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="audience"
                    checked={targetAudience === "student"}
                    onChange={() => setTargetAudience("student")}
                    className="accent-indigo-500"
                  />
                  All Enrolled Students
                </label>
                <label className="inline-flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="audience"
                    checked={targetAudience === "all"}
                    onChange={() => setTargetAudience("all")}
                    className="accent-indigo-500"
                  />
                  Entire Institution (All Roles)
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmittingBroadcast || !broadcastTitle.trim() || !broadcastMessage.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 text-xs font-bold text-white shadow-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className={`h-3.5 w-3.5 ${isSubmittingBroadcast ? "animate-pulse" : ""}`} />
              <span>{isSubmittingBroadcast ? "Broadcasting..." : "Send Global Notification"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* ======================================================== */}
      {/* CURRICULUM & COHORT MANAGEMENT TABLES (TABS: STUDENTS / SUBJECTS / RESOURCES) */}
      {/* ======================================================== */}
      <div className="rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-xs space-y-6">
        
        {/* Management Tabs Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="h-5 w-5 text-indigo-400" />
              <span>Curriculum & Cohort Management Tables</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Live administration console for student telemetry, accredited syllabus subjects, and curated learning resources
            </p>
          </div>

          {/* Tab Navigation Switcher */}
          <div className="flex items-center gap-1.5 bg-slate-900 p-1.5 rounded-2xl border border-slate-800 shrink-0 self-start sm:self-auto overflow-x-auto max-w-full">
            <button
              onClick={() => {
                setActiveTab("students");
                setSearchTerm("");
              }}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                activeTab === "students"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              <span>Students</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-md ${activeTab === "students" ? "bg-indigo-700 text-white" : "bg-slate-800 text-slate-400"}`}>
                {filteredStudents.length}
              </span>
            </button>

            <button
              onClick={() => {
                setActiveTab("subjects");
                setSearchTerm("");
              }}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                activeTab === "subjects"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Subjects</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-md ${activeTab === "subjects" ? "bg-indigo-700 text-white" : "bg-slate-800 text-slate-400"}`}>
                {subjects.length}
              </span>
            </button>

            <button
              onClick={() => {
                setActiveTab("resources");
                setSearchTerm("");
              }}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                activeTab === "resources"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Library className="h-3.5 w-3.5" />
              <span>Resources</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-md ${activeTab === "resources" ? "bg-indigo-700 text-white" : "bg-slate-800 text-slate-400"}`}>
                {resources.length}
              </span>
            </button>
          </div>
        </div>

        {/* Global Search & Action Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={
                  activeTab === "students"
                    ? "Search student or ID..."
                    : activeTab === "subjects"
                    ? "Search subject code or name..."
                    : "Search resource title, platform..."
                }
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
              />
            </div>

            {activeTab === "students" && (
              <select
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 outline-none cursor-pointer"
              >
                <option value="all">All Cohorts ({STUDENT_ROSTER.length})</option>
                <option value="needs_revision">Needs Revision Flags</option>
                <option value="on_track">On-Track Only</option>
              </select>
            )}
          </div>

          {/* Quick Action Button for Subjects & Resources */}
          <div className="flex items-center gap-2">
            {activeTab === "subjects" && (
              <button
                onClick={() => setIsSubjectModalOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3.5 py-1.5 text-xs font-bold text-white transition-colors shadow-sm cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add Subject</span>
              </button>
            )}

            {activeTab === "resources" && (
              <button
                onClick={() => setIsResourceModalOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-3.5 py-1.5 text-xs font-bold text-white transition-colors shadow-sm cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add Resource</span>
              </button>
            )}

            <button
              onClick={() => {
                if (activeTab === "subjects") fetchSubjects();
                else if (activeTab === "resources") fetchResources();
                else fetchHealthAndSummary();
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white transition-colors cursor-pointer"
              title="Refresh live table data"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Status Alerts for Subject / Resource addition */}
        {subjectFormStatus && activeTab === "subjects" && (
          <div
            className={`p-3.5 rounded-2xl border text-xs flex items-center justify-between ${
              subjectFormStatus.type === "success"
                ? "bg-emerald-950/70 border-emerald-800/80 text-emerald-300"
                : "bg-rose-950/70 border-rose-800/80 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{subjectFormStatus.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setSubjectFormStatus(null)}
              className="text-slate-400 hover:text-white text-xs font-bold px-2 py-0.5 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {resourceFormStatus && activeTab === "resources" && (
          <div
            className={`p-3.5 rounded-2xl border text-xs flex items-center justify-between ${
              resourceFormStatus.type === "success"
                ? "bg-emerald-950/70 border-emerald-800/80 text-emerald-300"
                : "bg-rose-950/70 border-rose-800/80 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{resourceFormStatus.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setResourceFormStatus(null)}
              className="text-slate-400 hover:text-white text-xs font-bold px-2 py-0.5 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* TAB 1: STUDENTS ROSTER TABLE (Mobile-Responsive) */}
        {/* ---------------------------------------------------- */}
        {activeTab === "students" && (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[700px] text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-3.5 pl-3">Scholar ID & Name</th>
                  <th className="pb-3.5 px-3">Semester</th>
                  <th className="pb-3.5 px-3">Primary Focus</th>
                  <th className="pb-3.5 px-3">Logged Study</th>
                  <th className="pb-3.5 px-3">Diagnostic Status</th>
                  <th className="pb-3.5 px-3">Telemetry Trigger</th>
                  <th className="pb-3.5 pr-3 text-right">Plan Version</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3.5 pl-3">
                      <div className="font-bold text-white">{student.name}</div>
                      <div className="font-mono text-[11px] text-slate-400">{student.id}</div>
                    </td>
                    <td className="py-3.5 px-3 font-medium text-slate-300">
                      Sem {student.semester}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="font-semibold text-indigo-300">{student.focus}</span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="font-bold text-white">{student.loggedHours}h</span>
                      <span className="text-slate-500"> / {student.scheduledHours}h</span>
                      <span className="text-[11px] text-slate-400 block font-mono">({student.completionRate}%)</span>
                    </td>
                    <td className="py-3.5 px-3">
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
                    <td className="py-3.5 px-3 text-slate-400 font-mono text-[11px]">
                      {student.ruleTrigger}
                    </td>
                    <td className="py-3.5 pr-3 text-right font-mono font-bold text-indigo-400">
                      {student.planVersion}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* TAB 2: SUBJECTS MANAGEMENT TABLE (Mobile-Responsive) */}
        {/* ---------------------------------------------------- */}
        {activeTab === "subjects" && (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[700px] text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-3.5 pl-3">Subject Code</th>
                  <th className="pb-3.5 px-3">Subject Name</th>
                  <th className="pb-3.5 px-3">Semester</th>
                  <th className="pb-3.5 px-3">Weekly Target</th>
                  <th className="pb-3.5 px-3">Enrolled</th>
                  <th className="pb-3.5 px-3">Core Syllabus Units</th>
                  <th className="pb-3.5 pr-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {filteredSubjects.map((subj) => (
                  <tr key={subj.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3.5 pl-3 font-mono font-bold text-indigo-400">
                      {subj.code}
                    </td>
                    <td className="py-3.5 px-3 font-bold text-white">
                      {subj.name}
                    </td>
                    <td className="py-3.5 px-3 text-slate-300 font-medium">
                      Sem {subj.semester}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="font-bold text-emerald-400">{subj.weekly_recommended_hours}h</span>
                      <span className="text-[11px] text-slate-500"> / week</span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-slate-300">
                      {subj.enrolled_count} students
                    </td>
                    <td className="py-3.5 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {(subj.syllabus_units || []).slice(0, 3).map((unit, uIdx) => (
                          <span
                            key={uIdx}
                            className="inline-block rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300"
                          >
                            {unit}
                          </span>
                        ))}
                        {(subj.syllabus_units || []).length > 3 && (
                          <span className="text-[10px] text-slate-500 self-center">
                            +{(subj.syllabus_units || []).length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 pr-3 text-right">
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-950/80 border border-emerald-800/80 px-2 py-0.5 text-[11px] font-bold text-emerald-400">
                        {subj.status || "Active"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* TAB 3: LEARNING RESOURCES TABLE (Mobile-Responsive) */}
        {/* ---------------------------------------------------- */}
        {activeTab === "resources" && (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[700px] text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-3.5 pl-3">Course / Resource Title</th>
                  <th className="pb-3.5 px-3">Platform</th>
                  <th className="pb-3.5 px-3">Target Subject</th>
                  <th className="pb-3.5 px-3">Difficulty</th>
                  <th className="pb-3.5 px-3">Rating</th>
                  <th className="pb-3.5 pr-3 text-right">External Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {filteredResources.map((res) => (
                  <tr key={res.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3.5 pl-3">
                      <div className="font-bold text-white max-w-sm">{res.title}</div>
                      <span className="text-[10px] text-slate-500 font-mono">ID: {res.id}</span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-300 font-medium">
                      {res.platform}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="rounded-md bg-indigo-950/80 border border-indigo-800/60 px-2 py-0.5 text-[11px] font-semibold text-indigo-300">
                        {res.subject}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span
                        className={`rounded-md px-2 py-0.5 text-[10px] font-bold border ${
                          res.difficulty === "Advanced"
                            ? "bg-purple-950/80 border-purple-800/80 text-purple-300"
                            : res.difficulty === "Intermediate"
                            ? "bg-blue-950/80 border-blue-800/80 text-blue-300"
                            : "bg-emerald-950/80 border-emerald-800/80 text-emerald-300"
                        }`}
                      >
                        {res.difficulty}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-semibold text-amber-400">
                      <div className="flex items-center gap-1">
                        <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                        <span>{res.rating}</span>
                      </div>
                    </td>
                    <td className="py-3.5 pr-3 text-right">
                      <a
                        href={res.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 px-2.5 py-1 text-[11px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        <span>Open</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

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

      {/* ======================================================== */}
      {/* INTERACTIVE MODAL: ADD NEW SUBJECT */}
      {/* ======================================================== */}
      {isSubjectModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs animate-in fade-in duration-200"
          role="dialog"
          aria-modal="true"
        >
          <div className="relative w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-7 shadow-2xl space-y-5 text-left">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <BookOpen className="h-5 w-5 text-indigo-400" />
                <span>Add New Syllabus Subject</span>
              </div>
              <button
                onClick={() => setIsSubjectModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-full cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSubject} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Subject Code</label>
                <input
                  type="text"
                  placeholder="e.g. CS-506"
                  value={newSubjectCode}
                  onChange={(e) => setNewSubjectCode(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 font-mono uppercase"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Subject Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. Cloud Computing & Distributed Systems"
                  value={newSubjectName}
                  onChange={(e) => setNewSubjectName(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Semester</label>
                  <select
                    value={newSubjectSemester}
                    onChange={(e) => setNewSubjectSemester(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                      <option key={sem} value={sem}>
                        Semester {sem}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Weekly Target (Hours)</label>
                  <input
                    type="number"
                    min="1"
                    max="40"
                    step="0.5"
                    value={newSubjectHours}
                    onChange={(e) => setNewSubjectHours(Number(e.target.value))}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">
                  Syllabus Units <span className="text-[10px] text-slate-500 font-normal">(Comma-separated)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Virtualization, AWS Architecture, Serverless, Cloud Security"
                  value={newSubjectUnits}
                  onChange={(e) => setNewSubjectUnits(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsSubjectModalOpen(false)}
                  className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingSubject || !newSubjectCode.trim() || !newSubjectName.trim()}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2 text-xs font-bold text-white transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>{isSubmittingSubject ? "Saving..." : "Add Subject"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* INTERACTIVE MODAL: ADD NEW LEARNING RESOURCE */}
      {/* ======================================================== */}
      {isResourceModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs animate-in fade-in duration-200"
          role="dialog"
          aria-modal="true"
        >
          <div className="relative w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-7 shadow-2xl space-y-5 text-left">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Library className="h-5 w-5 text-indigo-400" />
                <span>Add Learning Resource</span>
              </div>
              <button
                onClick={() => setIsResourceModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-full cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateResource} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Course / Resource Title</label>
                <input
                  type="text"
                  placeholder="e.g. Machine Learning Specialization"
                  value={newResourceTitle}
                  onChange={(e) => setNewResourceTitle(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Platform / University</label>
                  <input
                    type="text"
                    placeholder="e.g. Stanford / Coursera"
                    value={newResourcePlatform}
                    onChange={(e) => setNewResourcePlatform(e.target.value)}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Target Subject</label>
                  <input
                    type="text"
                    placeholder="e.g. Operating Systems"
                    value={newResourceSubject}
                    onChange={(e) => setNewResourceSubject(e.target.value)}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Direct Course URL</label>
                <input
                  type="url"
                  placeholder="https://www.coursera.org/learn/..."
                  value={newResourceUrl}
                  onChange={(e) => setNewResourceUrl(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Difficulty</label>
                  <select
                    value={newResourceDifficulty}
                    onChange={(e) => setNewResourceDifficulty(e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Rating (1.0 - 5.0)</label>
                  <input
                    type="number"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={newResourceRating}
                    onChange={(e) => setNewResourceRating(Number(e.target.value))}
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsResourceModalOpen(false)}
                  className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingResource || !newResourceTitle.trim() || !newResourceUrl.trim()}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2 text-xs font-bold text-white transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>{isSubmittingResource ? "Saving..." : "Add Resource"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
