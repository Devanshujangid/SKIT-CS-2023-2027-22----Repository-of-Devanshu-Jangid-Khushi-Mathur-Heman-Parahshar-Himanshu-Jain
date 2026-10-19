"use client";

import { useState, useEffect } from "react";
import { useUser, useAuth, UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import {
  BookOpen,
  Clock,
  Target,
  Sparkles,
  CalendarX2,
  RefreshCw,
  CheckSquare,
  Square,
  Calendar,
  CheckCircle2,
  TrendingUp,
  Award,
  UserCheck,
  Wifi,
  AlertCircle,
  Lightbulb,
  Milestone,
  Loader2,
  Printer,
  CalendarPlus,
  ExternalLink,
  GraduationCap,
  Star,
} from "lucide-react";

interface StatCardProps {
  icon?: React.ReactNode;
  title: string;
  value: string;
  subtitle?: string;
  isLoading?: boolean;
}

interface UserProfileState {
  semester?: number;
  study_hours_per_day?: number;
  goals?: string;
  subjects?: string[];
}

interface ScheduleTask {
  id: string;
  subject: string;
  topic: string;
  activity: string;
  duration_minutes: number;
  priority: "high" | "medium" | "low";
  completed?: boolean;
}

interface ScheduleDay {
  dayNumber: number;
  dayName: string;
  dateStr: string;
  tasks: ScheduleTask[];
}

interface RecommendedCourse {
  id: string;
  title: string;
  provider: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  rating: number;
  category: string;
  url: string;
}

const RECOMMENDED_COURSES: RecommendedCourse[] = [
  {
    id: "course-1",
    title: "Data Structures and Algorithms Specialization",
    provider: "UC San Diego & HSE University",
    difficulty: "Intermediate",
    rating: 4.8,
    category: "Data Structures",
    url: "https://www.coursera.org/specializations/data-structures-algorithms",
  },
  {
    id: "course-2",
    title: "Operating Systems and You: Becoming a Tech Support Pro",
    provider: "Google",
    difficulty: "Beginner",
    rating: 4.8,
    category: "Operating Systems",
    url: "https://www.coursera.org/learn/operating-systems",
  },
  {
    id: "course-3",
    title: "Computer Communications Specialization",
    provider: "University of Colorado Boulder",
    difficulty: "Intermediate",
    rating: 4.6,
    category: "Computer Networks",
    url: "https://www.coursera.org/specializations/computer-communications",
  },
  {
    id: "course-4",
    title: "Database Management Essentials",
    provider: "University of Colorado System",
    difficulty: "Beginner",
    rating: 4.7,
    category: "Databases",
    url: "https://www.coursera.org/learn/database-management",
  },
  {
    id: "course-5",
    title: "Machine Learning Specialization",
    provider: "DeepLearning.AI & Stanford",
    difficulty: "Beginner",
    rating: 4.9,
    category: "Machine Learning",
    url: "https://www.coursera.org/specializations/machine-learning-introduction",
  },
  {
    id: "course-6",
    title: "AWS Fundamentals: Building Serverless Applications",
    provider: "Amazon Web Services",
    difficulty: "Intermediate",
    rating: 4.7,
    category: "Cloud Computing",
    url: "https://www.coursera.org/learn/aws-fundamentals-building-serverless-applications",
  },
];

// Backend Plan API Models
interface PlanOverviewData {
  student_semester?: number;
  daily_target_hours?: number;
  weekly_total_hours?: number;
  primary_focus?: string;
  strategy_summary?: string;
}

interface BackendSession {
  subject: string;
  topic: string;
  duration_hours: number;
  activity_type: string;
  priority: "high" | "medium" | "low";
  id?: string;
  completed?: boolean;
  is_completed?: boolean;
  status?: string;
}

interface BackendDaySchedule {
  day: string;
  total_hours: number;
  sessions: BackendSession[];
}

interface MonthlyMilestone {
  week: number;
  milestone: string;
  key_deliverable: string;
}

interface BackendPlanData {
  plan_overview?: PlanOverviewData;
  weekly_schedule?: BackendDaySchedule[];
  monthly_milestones?: MonthlyMilestone[];
  study_tips?: string[];
  completed_task_ids?: string[];
}

interface PlanRecord {
  id: string;
  plan_data: BackendPlanData;
  created_at: string;
  updated_at: string;
}

// Map backend day names to day numbers
const DAY_NAME_TO_NUMBER: Record<string, number> = {
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
  Saturday: 6,
  Sunday: 7,
};

function formatActivityType(typeStr: string): string {
  if (!typeStr) return "Study Session";
  const map: Record<string, string> = {
    core_concept_study: "Core Concept Study",
    practice_problems: "Practice Problems",
    lecture_review: "Lecture Review",
    revision_quiz: "Revision Quiz",
  };
  if (map[typeStr]) return map[typeStr];
  return typeStr
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}


function parseWeeklySchedule(
  weeklySchedule: BackendDaySchedule[],
  databaseTasks: any[] = []
): ScheduleDay[] {
  return weeklySchedule.map((dayItem, dayIdx) => {
    const dayName = dayItem.day || `Day ${dayIdx + 1}`;
    const dayNumber = DAY_NAME_TO_NUMBER[dayName] || dayIdx + 1;

    const tasks: ScheduleTask[] = (dayItem.sessions || []).map(
      (sess, sessIdx) => {
        const subject = sess.subject || "General Study";
        const topic = sess.topic || "Core Topic";
        const durationMins = Math.round((sess.duration_hours || 1) * 60);

        // Find the corresponding persisted database task by title.
        const expectedTitle = `${subject}: ${topic}`.trim().toLowerCase();

        const dbTask = databaseTasks.find(
          (task) =>
            String(task.title || "").trim().toLowerCase() === expectedTitle
        );

        const isDone = dbTask
          ? Boolean(dbTask.is_completed)
          : Boolean(
              sess.completed ||
              sess.is_completed ||
              sess.status === "completed"
            );

        return {
          id: dbTask?.id || sess.id || `live-d${dayNumber}-t${sessIdx + 1}`,
          subject,
          topic,
          activity: formatActivityType(sess.activity_type),
          duration_minutes: durationMins,
          priority: sess.priority || "medium",
          completed: isDone,
        };
      }
    );

    return {
      dayNumber,
      dayName,
      dateStr: `Day ${dayNumber}`,
      tasks,
    };
  });
}


function normalizeRecommendation(item: any, index: number): RecommendedCourse {
  const title = item.title || item.course_name || item["Course Name"] || item.name || "Recommended Course";
  const provider = item.provider || item.university || item["University"] || "Online Course";

  let rawDiff: "Beginner" | "Intermediate" | "Advanced" = "Beginner";
  const diffStr = (item.difficulty || item.difficulty_level || item["Difficulty Level"] || "Beginner").toString().toLowerCase();
  if (diffStr.includes("adv")) rawDiff = "Advanced";
  else if (diffStr.includes("inter")) rawDiff = "Intermediate";
  else rawDiff = "Beginner";

  const rawRating = item.rating ?? item.course_rating ?? item["Course Rating"];
  const parsedRating = typeof rawRating === "number" ? rawRating : parseFloat(rawRating) || 4.7;

  const category = item.category || item.skills || item["Skills"] || item.subject || "Curated Resource";
  const url = item.url || item.course_url || item["Course URL"] || item.link || "#";

  return {
    id: item.id ? String(item.id) : `rec-${index + 1}`,
    title,
    provider,
    difficulty: rawDiff,
    rating: Number(parsedRating.toFixed(1)),
    category: typeof category === "string" ? category.split(",")[0].trim() : "Curated",
    url,
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoaded: isUserLoaded } = useUser();
  const { getToken, isLoaded: isAuthLoaded, isSignedIn } = useAuth();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [completedTaskIds, setCompletedTaskIds] = useState<string[]>([]);
  const [hasPlan, setHasPlan] = useState<boolean>(false);
  const [userProfile, setUserProfile] = useState<UserProfileState | null>(null);

  // Live Plan Data State from GET /api/v1/plans
  const [schedule, setSchedule] = useState<ScheduleDay[]>([]);
  const [planOverview, setPlanOverview] = useState<PlanOverviewData | null>(null);
  const [monthlyMilestones, setMonthlyMilestones] = useState<MonthlyMilestone[]>([]);
  const [studyTips, setStudyTips] = useState<string[]>([]);
  const [plans, setPlans] = useState<PlanRecord[]>([]);
  const [isFetchingPlans, setIsFetchingPlans] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isLiveSynced, setIsLiveSynced] = useState<boolean>(false);

  // AI Plan Generation State
  const [isGeneratingPlan, setIsGeneratingPlan] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Live Recommendations State from GET /api/v1/recommendations
  const [recommendations, setRecommendations] = useState<RecommendedCourse[]>(RECOMMENDED_COURSES);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState<boolean>(true);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);

  // Load saved user profile from localStorage
  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("slp_user_profile");
      if (savedProfile) {
        setUserProfile(JSON.parse(savedProfile));
      }
    } catch (e) {
      console.error("Failed to load user profile from localStorage:", e);
    }
  }, []);

  // Fetch live recommendations from GET /api/v1/recommendations with Clerk JWT
  const fetchRecommendations = async () => {
    setIsLoadingRecommendations(true);
    setRecommendationsError(null);

    try {
      const token = await getToken();
      console.log("Signed in:", isSignedIn);
      console.log("Token available:", Boolean(token));
      if (!token) {
    throw new Error("Please sign in again to load recommendations.");
  }

  const savedProfile = localStorage.getItem("slp_user_profile");
  const profile = savedProfile ? JSON.parse(savedProfile) : null;

  const subjects = Array.isArray(profile?.subjects)
    ? profile.subjects
    : [];

  const query = subjects.join(" ").trim();

  if (!query) {
    setRecommendations([]);
    return;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/recommendations?query=${encodeURIComponent(query)}&top_n=5`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    }
  );
      if (!response.ok) {
        throw new Error(`GET /api/v1/recommendations returned status ${response.status}`);
      }

      const data = await response.json();
      let recList: any[] = [];

      if (Array.isArray(data)) {
        recList = data;
      } else if (Array.isArray(data.recommendations)) {
        recList = data.recommendations;
      } else if (Array.isArray(data.courses)) {
        recList = data.courses;
      } else if (Array.isArray(data.data)) {
        recList = data.data;
      } else if (Array.isArray(data.results)) {
        recList = data.results;
      }

      if (recList.length > 0) {
        setRecommendations(recList.map(normalizeRecommendation));
      }
    } catch (err: any) {
      console.error("Error fetching live recommendations:", err);
      setRecommendationsError(err.message || "Failed to load recommendations");
    } finally {
      setIsLoadingRecommendations(false);
    }
  };

  // Fetch live study plans from GET /api/v1/plans with Clerk JWT
  const fetchPlans = async () => {
    setIsFetchingPlans(true);
    setFetchError(null);

    try {
      // Securely acquire Clerk JWT token
      const token = await getToken();

      const response = await fetch(`${API_BASE_URL}/api/v1/plans`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`GET /api/v1/plans returned status ${response.status}`);
      }

      const data = await response.json();

      if (data.success && Array.isArray(data.plans)) {
        setPlans(data.plans);
        setIsLiveSynced(true);

        if (data.plans.length > 0) {
          // Process latest generated study plan
          const latestPlan = data.plans[data.plans.length - 1];
          let planData: BackendPlanData | null = null;

          if (typeof latestPlan.plan_data === "string") {
            try {
              planData = JSON.parse(latestPlan.plan_data);
            } catch (e) {
              console.error("Failed to parse plan_data string:", e);
            }
          } else {
            planData = latestPlan.plan_data;
          }
          

          if (planData) {
            if (planData.plan_overview) {
              setPlanOverview(planData.plan_overview);
            }
            if (planData.monthly_milestones) {
              setMonthlyMilestones(planData.monthly_milestones);
            }
            if (planData.study_tips) {
              setStudyTips(planData.study_tips);
            }
            if (planData.weekly_schedule && planData.weekly_schedule.length > 0) {
                  const planAny = planData as any;

            // Fetch persisted tasks with their real database IDs
                  const token = await getToken();
                  const tasksResponse = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
                  headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

                   let databaseTasks: any[] = [];

                   if (tasksResponse.ok) {
                       const tasksData = await tasksResponse.json();
                       databaseTasks = tasksData.tasks || [];
                } else {
                        console.error("Failed to fetch database tasks:", tasksResponse.status);
                }

                  const mappedSchedule = parseWeeklySchedule(
                  planData.weekly_schedule,
                  databaseTasks
                    );

                  setSchedule(mappedSchedule);
                  setHasPlan(true);

                  const doneIds = mappedSchedule
                 .flatMap((d) => d.tasks)
                  .filter((t) => t.completed)
                  .map((t) => t.id);

                   setCompletedTaskIds(doneIds);
               }
          }
        } else {
          // User has no study plans in database
          setHasPlan(false);
        }
      } else {
        setFetchError("API returned unsuccessful payload format");
      }
    } catch (err: any) {
      console.error("Error fetching live study plans:", err);
      setFetchError(err.message || "Network error fetching study plans");
    } finally {
      setIsFetchingPlans(false);
      setIsLoading(false);
    }
  };

  // Database Persistence: Update task status via PATCH /api/v1/tasks/{id}/status
  const toggleTaskCompletion = async (taskId: string) => {
    const isCurrentlyCompleted = completedTaskIds.includes(taskId);
    const nextCompleted = !isCurrentlyCompleted;

    // 1. Optimistic UI update: update local React state immediately
    setCompletedTaskIds((prev) =>
      nextCompleted ? [...prev, taskId] : prev.filter((id) => id !== taskId)
    );

    
     console.log("Task clicked:", taskId);
     // Temporary tasks are not saved in the database.
    if (String(taskId).startsWith("live-d")) {
      console.log("Temporary task — PATCH skipped:", taskId);
    return;
    }

    // 2. Send PATCH request to backend with Clerk JWT
    try {
      const token = await getToken();

      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${encodeURIComponent(taskId)}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          is_completed: nextCompleted,
        }),
      });

      if (!response.ok) {
        throw new Error(`PATCH /api/v1/tasks/${taskId}/status returned status ${response.status}`);
      }
    } catch (err: any) {
      console.error(`Failed to update task ${taskId} status:`, err);

      // 3. Rollback / Revert local React state if API request fails
      setCompletedTaskIds((prev) =>
        isCurrentlyCompleted
          ? (prev.includes(taskId) ? prev : [...prev, taskId])
          : prev.filter((id) => id !== taskId)
      );
    }
  };

  // Call POST /api/v1/ai/generate-plan endpoint to generate new 7-Day Study Plan with Gemini AI
  const handleGeneratePlan = async () => {
    // Prevent duplicate triggers if generation is already in progress
    if (isGeneratingPlan) return;

    setIsGeneratingPlan(true);
    setGenerationError(null);

    try {
      const token = await getToken();

      // Build onboarding data payload using saved userProfile or intelligent fallbacks
      const onboardingData = {
        semester: userProfile?.semester ? Number(userProfile.semester) : 1,
        study_hours_per_day: userProfile?.study_hours_per_day ? Number(userProfile.study_hours_per_day) : 4,
        goals: userProfile?.goals
          ? (Array.isArray(userProfile.goals) ? userProfile.goals : [userProfile.goals])
          : ["Master core academic subjects and maintain high academic performance"],
        subjects: userProfile?.subjects && userProfile.subjects.length > 0
          ? userProfile.subjects
          : ["Data Structures", "Operating Systems", "Computer Networks"],
      };

      const response = await fetch(`${API_BASE_URL}/api/v1/ai/generate-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ onboarding_data: onboardingData }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let detail = `Server returned status ${response.status}`;
        try {
          const parsed = JSON.parse(errorText);
          if (parsed.detail) detail = parsed.detail;
        } catch {
          if (errorText) detail = errorText;
        }
        throw new Error(detail);
      }

      const data = await response.json();

      if (data.success) {
        // Poll backend async generation status until completion before fetching plan
        let attempts = 0;
        let isDone = false;
        while (attempts < 20 && !isDone) {
          await new Promise((r) => setTimeout(r, 1500));
          attempts++;
          try {
            const statusRes = await fetch(`${API_BASE_URL}/api/v1/ai/generation-status`, {
              headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
            });
            if (statusRes.ok) {
              const statusData = await statusRes.json();
              if (statusData.status === "completed") {
                isDone = true;
              } else if (statusData.status === "failed") {
                throw new Error(statusData.message || "Plan generation failed on server");
              }
            }
          } catch (statusErr: any) {
            if (statusErr.message && statusErr.message.includes("failed")) throw statusErr;
          }
        }

        // Automatically fetch live plans and recommendations to render updated dashboard
        await fetchPlans();
        await fetchRecommendations();
      } else {
        throw new Error("Plan generation completed but response payload was invalid.");
      }
    } catch (err: any) {
      console.error("Failed to generate AI study plan:", err);
      const errMsg = err.message || "Failed to generate AI study plan. Please try again.";
      setGenerationError(errMsg);
      alert(`Error generating AI plan: ${errMsg}`);
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  // Trigger live data fetch on mount & whenever auth is ready
  useEffect(() => {
    if (isAuthLoaded) {
      fetchPlans();
      fetchRecommendations();
    } else {
      // Fallback timer if auth load takes long
      const timer = setTimeout(() => {
        setIsLoading(false);
        setIsLoadingRecommendations(false);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [isAuthLoaded, isSignedIn]);

  const toggleLoading = () => setIsLoading((prev) => !prev);
  const togglePlanState = () => setHasPlan((prev) => !prev);

  // Native PDF Export (Print View)
  const handleExportPDF = () => {
    window.print();
  };

  // Native iCalendar (.ics Blob) Export
  const handleExportICS = () => {
    if (!activeSchedule || activeSchedule.length === 0) return;

    const now = new Date();
    const formatDate = (date: Date) =>
      date.toISOString().replace(/-|:|\.\d+/g, "").slice(0, 15) + "Z";

    const icsLines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Smart Learning Planner//Academic Schedule//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      "X-WR-CALNAME:Smart 7-Day Study Plan",
    ];

    const baseDate = new Date();
    baseDate.setHours(9, 0, 0, 0);

    activeSchedule.forEach((daySchedule, dayIdx) => {
      const eventDate = new Date(baseDate);
      eventDate.setDate(baseDate.getDate() + dayIdx);

      let currentHour = 9;

      daySchedule.tasks.forEach((task) => {
        const startDate = new Date(eventDate);
        startDate.setHours(currentHour, 0, 0, 0);

        const durationMins = task.duration_minutes || 60;
        const endDate = new Date(startDate.getTime() + durationMins * 60 * 1000);

        currentHour += Math.ceil(durationMins / 60);

        const dtStart = formatDate(startDate);
        const dtEnd = formatDate(endDate);
        const summary = `[${task.subject}] ${task.topic}`;
        const description = `Activity: ${task.activity}\\nPriority: ${task.priority.toUpperCase()}\\nDuration: ${task.duration_minutes} minutes`;

        icsLines.push(
          "BEGIN:VEVENT",
          `UID:slp-${task.id}-${startDate.getTime()}@smartlearningplanner`,
          `DTSTAMP:${formatDate(now)}`,
          `DTSTART:${dtStart}`,
          `DTEND:${dtEnd}`,
          `SUMMARY:${summary}`,
          `DESCRIPTION:${description}`,
          "STATUS:CONFIRMED",
          "END:VEVENT"
        );
      });
    });

    icsLines.push("END:VCALENDAR");

    const blob = new Blob([icsLines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "smart_study_plan.ics");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Calculate totals & completion metrics based on live schedule
  const activeSchedule = schedule;
  const allTasks = activeSchedule.flatMap((day) => day.tasks);
  const totalTasksCount = allTasks.length;
  const completedTasksCount = completedTaskIds.filter((id) => allTasks.some((t) => t.id === id)).length;
  const weeklyProgressPercent = totalTasksCount > 0
    ? Math.round((completedTasksCount / totalTasksCount) * 100)
    : 0;

  const currentDaySchedule = activeSchedule.find((d) => d.dayNumber === selectedDay) || activeSchedule[0];
  const dayCompletedCount = currentDaySchedule ? currentDaySchedule.tasks.filter((t) => completedTaskIds.includes(t.id)).length : 0;
  const dayTotalCount = currentDaySchedule ? currentDaySchedule.tasks.length : 0;

  if (isLoading || !isUserLoaded) {
    return <DashboardSkeleton onToggleLoading={toggleLoading} />;
  }

  // Dynamic metric values based on live plan, user profile or defaults
  const displaySemester = planOverview?.student_semester
    ? `Semester ${planOverview.student_semester}`
    : userProfile?.semester
      ? `Semester ${userProfile.semester}`
      : "N/A";

  const displayWeeklyHours = planOverview?.weekly_total_hours
    ? `${planOverview.weekly_total_hours} hrs`
    : userProfile?.study_hours_per_day
      ? `${(userProfile.study_hours_per_day * 7).toFixed(1)} hrs`
      : "0 hrs";

  const displayDailyHoursSubtitle = planOverview?.daily_target_hours
    ? `${planOverview.daily_target_hours} hrs/day target`
    : userProfile?.study_hours_per_day
      ? `${userProfile.study_hours_per_day} hrs/day target`
      : "No target set";

  const displayFocusSubject = planOverview?.primary_focus
    ? planOverview.primary_focus
    : (userProfile?.subjects && userProfile.subjects.length > 0)
      ? userProfile.subjects[0]
      : "General Study";

  return (
    <main className="min-h-screen bg-slate-50 p-6 sm:p-8 print:bg-white print:p-0">
      <div className="mx-auto max-w-6xl space-y-8 print:space-y-4">
        
        {/* Testing & Navigation Control Bar with Live API Status */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm print:hidden">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <span>Smart Planner Dashboard</span>
            </div>

            {/* Live API Sync Badge */}
            <div className="flex items-center gap-1.5 text-xs font-medium">
              {isFetchingPlans ? (
                <span className="inline-flex items-center gap-1 text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Fetching live plans...
                </span>
              ) : isLiveSynced ? (
                <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                  <Wifi className="h-3 w-3 text-emerald-600" />
                  GET /api/v1/plans Synced
                </span>
              ) : fetchError ? (
                <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200" title={fetchError}>
                  <AlertCircle className="h-3 w-3 text-amber-600" />
                  Offline Preview
                </span>
              ) : null}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => {
                fetchPlans();
                fetchRecommendations();
              }}
              disabled={isFetchingPlans || isLoadingRecommendations}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 shadow-sm transition-colors cursor-pointer disabled:opacity-50"
              title="Refresh live study plan and recommendation data from backend API"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${(isFetchingPlans || isLoadingRecommendations) ? "animate-spin text-indigo-600" : ""}`} />
              Refetch API
            </button>
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
            >
              <UserCheck className="h-3.5 w-3.5 text-indigo-600" />
              Edit Profile / Onboarding
            </Link>
            <button
              onClick={togglePlanState}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              {hasPlan ? "Show Empty State" : "Show Active Plan"}
            </button>
            <button
              onClick={toggleLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Toggle Skeleton View
            </button>
            <button
              onClick={() => setIsLoadingRecommendations((prev) => !prev)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
              title="Toggle Recommended Resources skeleton state"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Toggle Courses Skeleton
            </button>
          </div>
        </div>

        {/* Header Section */}
        <header className="flex items-center justify-between rounded-2xl bg-white p-6 shadow-sm print:shadow-none print:border print:border-slate-200 print:p-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl print:text-xl">
              Welcome back, {user?.firstName || user?.username || "Student"}! 👋
            </h1>
            <p className="mt-1 text-slate-600 print:text-xs">
              {planOverview?.strategy_summary || "Let's map out your academic success."}
            </p>
          </div>
          <div className="print:hidden">
            <UserButton appearance={{ elements: { avatarBox: "h-12 w-12" } }} />
          </div>
        </header>

        {/* Profile Summary Stat Bar */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 print:grid-cols-4 print:gap-2">
          <StatCard
            icon={<Clock className="h-6 w-6" />}
            title="Total Weekly Hours"
            value={displayWeeklyHours}
            subtitle={displayDailyHoursSubtitle}
          />
          <StatCard
            icon={<Target className="h-6 w-6" />}
            title="Primary Focus"
            value={displayFocusSubject}
            subtitle="High priority"
          />
          <StatCard
            icon={<BookOpen className="h-6 w-6" />}
            title="Active Semester"
            value={displaySemester}
            subtitle="Fall 2026"
          />
          <StatCard
            icon={<Award className="h-6 w-6" />}
            title="Weekly Completion"
            value={`${weeklyProgressPercent}%`}
            subtitle={`${completedTasksCount} of ${totalTasksCount} tasks done`}
          />
        </section>

        {/* Main Section */}
        {!hasPlan ? (
          /* Empty State Hero View */
          <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="flex flex-col justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-700 p-8 text-white shadow-sm lg:col-span-2">
              <div className="max-w-lg">
                <h2 className="mb-4 text-3xl font-bold tracking-tight">Your study plan is empty.</h2>
                <p className="mb-8 text-indigo-100">
                  Generate your first 7-day personalized academic schedule using Gemini AI. We will analyze your goals and available hours to build the perfect timetable.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    if (!userProfile || !userProfile.subjects || userProfile.subjects.length === 0) {
                      router.push("/onboarding");
                    } else {
                      handleGeneratePlan();
                    }
                  }}
                  disabled={isGeneratingPlan}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 cursor-pointer shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isGeneratingPlan ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                      <span>Generating your plan...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-5 w-5" />
                      <span>Generate 7-Day Study Plan</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-8 text-center shadow-sm border border-slate-100">
              <div className="mb-4 rounded-full bg-slate-100 p-4">
                <CalendarX2 className="h-8 w-8 text-slate-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">No tasks for today</h3>
              <p className="mt-2 text-sm text-slate-500">
                Generate your AI study plan to populate your daily schedule.
              </p>
            </div>
          </section>
        ) : (
          /* Interactive 7-Day Timetable Grid Section */
          <section className="space-y-6">

            {/* Timetable Header & Progress Card */}
            <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 print:shadow-none print:border-slate-300 print:p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Calendar className="h-6 w-6 text-indigo-600 print:h-5 print:w-5" />
                      <h2 className="text-xl font-bold text-slate-900 print:text-lg">7-Day Interactive Academic Schedule</h2>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 print:hidden">
                      <button
                        type="button"
                        onClick={handleGeneratePlan}
                        disabled={isGeneratingPlan}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
                        title="Generate a fresh 7-day schedule using Gemini AI"
                      >
                        {isGeneratingPlan ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                            <span>Generating...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                            <span>Regenerate AI Plan</span>
                          </>
                        )}
                      </button>

                      {/* Export to PDF Button */}
                      <button
                        type="button"
                        onClick={handleExportPDF}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer shadow-xs"
                        title="Save schedule as PDF or print"
                      >
                        <Printer className="h-3.5 w-3.5 text-slate-600" />
                        <span>Save as PDF</span>
                      </button>

                      {/* Add to Calendar (.ics) Button */}
                      <button
                        type="button"
                        onClick={handleExportICS}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors cursor-pointer shadow-xs"
                        title="Export 7-day schedule to your calendar (.ics)"
                      >
                        <CalendarPlus className="h-3.5 w-3.5 text-indigo-600" />
                        <span>Add to Calendar</span>
                      </button>
                    </div>
                  </div>
                  <p className="mt-1 text-sm text-slate-500 print:hidden">
                    Track your daily study tasks. Check off topics as you complete them.
                  </p>
                </div>

                {/* Progress bar container */}
                <div className="w-full sm:w-64 space-y-2 rounded-xl bg-slate-50 p-3 border border-slate-100">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3.5 w-3.5 text-indigo-600" /> Overall Progress
                    </span>
                    <span className="text-indigo-600 font-bold">{weeklyProgressPercent}%</span>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-500"
                      style={{ width: `${weeklyProgressPercent}%` }}
                    />
                  </div>
                  <div className="text-right text-[11px] text-slate-400">
                    {completedTasksCount} / {totalTasksCount} tasks completed
                  </div>
                </div>
              </div>

              {/* 7-Day Navigation Tabs */}
              <div className="mt-6 flex items-center gap-2 overflow-x-auto pb-2 border-t border-slate-100 pt-4 print:hidden hide-scrollbar">
                {activeSchedule.map((d) => {
                  const dayTasks = d.tasks;
                  const dayDone = dayTasks.filter((t) => completedTaskIds.includes(t.id)).length;
                  const isAllDone = dayTasks.length > 0 && dayDone === dayTasks.length;
                  const isSelected = selectedDay === d.dayNumber;

                  return (
                    <button
                      key={d.dayNumber}
                      onClick={() => setSelectedDay(d.dayNumber)}
                      className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all cursor-pointer border whitespace-nowrap ${
                        isSelected
                          ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                          : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300"
                        }`}
                    >
                      <span>{d.dayName}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                          isSelected
                            ? "bg-indigo-700 text-indigo-100"
                            : isAllDone
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {isAllDone ? "✓" : `${dayDone}/${dayTasks.length}`}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Daily Schedule Task List */}
            {currentDaySchedule && (
              <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <span>{currentDaySchedule.dayName} Schedule</span>
                      <span className="text-xs font-medium text-slate-400">({currentDaySchedule.dateStr})</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {dayCompletedCount} of {dayTotalCount} tasks completed for today
                    </p>
                  </div>

                  {dayCompletedCount === dayTotalCount && dayTotalCount > 0 && (
                    <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200 self-start sm:self-auto">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      Day Completed!
                    </div>
                  )}
                </div>

                {/* Task Cards Stack */}
                <div className="space-y-3">
                  {currentDaySchedule.tasks.map((task) => {
                    const isCompleted = completedTaskIds.includes(task.id);

                    return (
                      <div
                        key={task.id}
                        onClick={() => toggleTaskCompletion(task.id)}
                        className={`group flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 rounded-xl p-4 transition-all border cursor-pointer ${
                          isCompleted
                            ? "bg-slate-50 border-slate-200 opacity-75"
                            : "bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm"
                        }`}
                      >
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          {/* Stateful Checkbox */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleTaskCompletion(task.id);
                            }}
                            className="mt-0.5 shrink-0 text-slate-400 hover:text-indigo-600 transition-colors cursor-pointer"
                            aria-label={isCompleted ? "Mark task as incomplete" : "Mark task as complete"}
                          >
                            {isCompleted ? (
                              <CheckSquare className="h-6 w-6 text-indigo-600" />
                            ) : (
                              <Square className="h-6 w-6 text-slate-300 group-hover:text-slate-400" />
                            )}
                          </button>

                          {/* Task Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md ${
                                  isCompleted
                                    ? "bg-slate-200 text-slate-500 line-through"
                                    : "bg-indigo-50 text-indigo-700"
                                }`}
                              >
                                {task.subject}
                              </span>

                              <span className="text-xs font-medium text-slate-400">• {task.activity}</span>

                              {/* Priority Badge */}
                              <PriorityBadge priority={task.priority} isCompleted={isCompleted} />
                            </div>

                            <h4
                              className={`mt-1.5 text-sm sm:text-base font-semibold transition-colors ${
                                isCompleted ? "text-slate-400 line-through" : "text-slate-900"
                              }`}
                            >
                              {task.topic}
                            </h4>
                          </div>
                        </div>

                        {/* Duration Tag */}
                        <div className="flex shrink-0 items-center gap-1 text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg self-start sm:self-center">
                          <Clock className="h-3.5 w-3.5 text-slate-400" />
                          <span>{task.duration_minutes} mins</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Monthly Milestones & Study Tips Grid (when present in plan) */}
            {(monthlyMilestones.length > 0 || studyTips.length > 0) && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {monthlyMilestones.length > 0 && (
                  <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-4">
                    <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                      <Milestone className="h-5 w-5 text-indigo-600" />
                      <h3 className="text-lg font-bold text-slate-900">Monthly Milestones</h3>
                    </div>
                    <div className="space-y-3">
                      {monthlyMilestones.map((m, i) => (
                        <div key={i} className="rounded-xl bg-slate-50 p-3.5 border border-slate-100">
                          <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase">
                            <span>Week {m.week}</span>
                          </div>
                          <p className="mt-1 text-sm font-semibold text-slate-800">{m.milestone}</p>
                          <p className="mt-0.5 text-xs text-slate-500">Deliverable: {m.key_deliverable}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {studyTips.length > 0 && (
                  <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-4">
                    <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                      <Lightbulb className="h-5 w-5 text-amber-500" />
                      <h3 className="text-lg font-bold text-slate-900">AI Study Recommendations</h3>
                    </div>
                    <ul className="space-y-2.5 text-sm text-slate-600">
                      {studyTips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-2 rounded-lg bg-amber-50/50 p-3 text-amber-900 border border-amber-100">
                          <span className="text-amber-500 font-bold">•</span>
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

          </section>
        )}

        {/* Recommended Resources UI Section (Coursera Courses) */}
        <section className="space-y-4 print:hidden">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <GraduationCap className="h-5 w-5 text-indigo-600 shrink-0" />
                <h2 className="text-lg sm:text-xl font-bold text-slate-900">Recommended Resources</h2>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                Curated Coursera courses aligned with your academic curriculum and study goals.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-slate-400 hidden sm:inline-block">
                Scroll horizontally for more courses →
              </span>
            </div>
          </div>

          {isLoadingRecommendations ? (
            /* Horizontal Scrolling Skeleton Loader */
            <div className="flex gap-3 sm:gap-4 overflow-x-auto pb-4 scroll-smooth animate-pulse">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="shrink-0 w-72 sm:w-80 md:w-84 rounded-2xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-5 w-20 rounded-md bg-slate-200" />
                    <div className="h-4 w-4 rounded bg-slate-200" />
                  </div>
                  <div className="space-y-2">
                    <div className="h-4 w-full rounded bg-slate-200" />
                    <div className="h-4 w-3/4 rounded bg-slate-200" />
                  </div>
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                    <div className="h-3.5 w-28 rounded bg-slate-100" />
                    <div className="h-3.5 w-10 rounded bg-slate-100" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Horizontal Scrolling Coursera Course Cards Grid */
            <div className="flex gap-3 sm:gap-4 overflow-x-auto pb-4 scroll-smooth">
              {recommendations.map((course) => (
                <a
                  key={course.id}
                  href={course.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group shrink-0 w-72 sm:w-80 md:w-84 rounded-2xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between whitespace-normal cursor-pointer"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <CourseDifficultyBadge difficulty={course.difficulty} />
                      <span className="text-slate-400 group-hover:text-indigo-600 transition-colors">
                        <ExternalLink className="h-4 w-4" />
                      </span>
                    </div>

                    <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-600 mb-1 block">
                      Coursera • {course.category}
                    </span>

                    <h3 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2 leading-snug">
                      {course.title}
                    </h3>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                    <span className="truncate max-w-[140px] sm:max-w-[170px] md:max-w-[190px]" title={course.provider}>
                      {course.provider}
                    </span>
                    <span className="font-semibold text-slate-700 flex items-center gap-1 shrink-0">
                      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                      {course.rating.toFixed(1)}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          )}
        </section>

      </div>

      {/* High Visibility Generating Plan Loading Modal Overlay */}
      {isGeneratingPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 print:hidden">
          <div className="flex max-w-md flex-col items-center rounded-2xl bg-white p-8 text-center shadow-2xl border border-slate-100 animate-in fade-in zoom-in duration-200">
            <div className="relative mb-4 flex items-center justify-center">
              <div className="absolute h-16 w-16 animate-ping rounded-full bg-indigo-100 opacity-75"></div>
              <div className="relative rounded-full bg-indigo-600 p-4 text-white shadow-lg">
                <Sparkles className="h-8 w-8 animate-spin" />
              </div>
            </div>
            <h3 className="text-xl font-bold text-slate-900">Generating Your AI Study Plan</h3>
            <p className="mt-2 text-sm text-slate-600">
              Gemini AI is analyzing your goals, subjects, and daily hours to build an optimized 7-day academic schedule...
            </p>
            <div className="mt-6 flex items-center gap-2 rounded-xl bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-600 border border-indigo-100">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generating plan... Please wait</span>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

// Course Difficulty Badge Component
function CourseDifficultyBadge({ difficulty }: { difficulty: "Beginner" | "Intermediate" | "Advanced" }) {
  const styles = {
    Beginner: "bg-emerald-50 text-emerald-700 border-emerald-200",
    Intermediate: "bg-blue-50 text-blue-700 border-blue-200",
    Advanced: "bg-purple-50 text-purple-700 border-purple-200",
  };

  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border capitalize ${styles[difficulty]}`}>
      {difficulty}
    </span>
  );
}

// Priority Badge Component
function PriorityBadge({ priority, isCompleted }: { priority: "high" | "medium" | "low"; isCompleted: boolean }) {
  if (isCompleted) {
    return (
      <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-400">
        {priority}
      </span>
    );
  }

  const styles = {
    high: "bg-rose-50 text-rose-700 border-rose-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    low: "bg-blue-50 text-blue-700 border-blue-200",
  };

  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border capitalize ${styles[priority]}`}>
      {priority} priority
    </span>
  );
}

// Reusable Widget Component with Skeleton State Support
function StatCard({ icon, title, value, subtitle, isLoading }: StatCardProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-4 rounded-2xl bg-white p-6 shadow-sm animate-pulse print:hidden">
        <div className="h-12 w-12 rounded-lg bg-slate-200 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-24 rounded bg-slate-200" />
          <div className="h-6 w-16 rounded bg-slate-200" />
          <div className="h-3 w-20 rounded bg-slate-200" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 rounded-2xl bg-white p-6 shadow-sm transition-all hover:shadow-md print:shadow-none print:border print:border-slate-200 print:p-3">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 print:h-8 print:w-8">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500 print:text-xs">{title}</p>
        <p className="text-xl font-bold text-slate-900 print:text-base">{value}</p>
        {subtitle && <p className="mt-0.5 text-xs text-slate-400 print:text-[10px]">{subtitle}</p>}
      </div>
    </div>
  );
}

// Loading Skeleton Component
function DashboardSkeleton({ onToggleLoading }: { onToggleLoading?: () => void }) {
  return (
    <main className="min-h-screen bg-slate-50 p-6 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-8 animate-pulse">

        {/* Testing / Preview Control */}
        {onToggleLoading && (
          <div className="flex justify-end">
            <button
              onClick={onToggleLoading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Toggle Loaded View
            </button>
          </div>
        )}

        {/* Header Skeleton */}
        <header className="flex items-center justify-between rounded-2xl bg-white p-6 shadow-sm">
          <div className="space-y-2">
            <div className="h-8 w-64 rounded-md bg-slate-200" />
            <div className="h-4 w-48 rounded-md bg-slate-200" />
          </div>
          <div className="h-12 w-12 rounded-full bg-slate-200" />
        </header>

        {/* 4-Card Metric Grid Skeleton */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="" value="" isLoading={true} />
          <StatCard title="" value="" isLoading={true} />
          <StatCard title="" value="" isLoading={true} />
          <StatCard title="" value="" isLoading={true} />
        </section>

        {/* Main Dashboard Section Skeleton */}
        <section className="space-y-6">
          <div className="rounded-2xl bg-white p-6 shadow-sm min-h-[140px] space-y-4">
            <div className="h-6 w-1/3 bg-slate-200 rounded-md" />
            <div className="flex gap-2">
              <div className="h-10 w-24 bg-slate-200 rounded-xl" />
              <div className="h-10 w-24 bg-slate-200 rounded-xl" />
              <div className="h-10 w-24 bg-slate-200 rounded-xl" />
              <div className="h-10 w-24 bg-slate-200 rounded-xl" />
            </div>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm min-h-[300px] space-y-4">
            <div className="h-6 w-48 bg-slate-200 rounded-md" />
            <div className="h-16 w-full bg-slate-100 rounded-xl" />
            <div className="h-16 w-full bg-slate-100 rounded-xl" />
            <div className="h-16 w-full bg-slate-100 rounded-xl" />
          </div>
        </section>

        {/* Recommended Resources Skeleton */}
        <section className="space-y-4 print:hidden">
          <div className="space-y-2">
            <div className="h-6 w-56 bg-slate-200 rounded-md" />
            <div className="h-4 w-80 bg-slate-200 rounded-md" />
          </div>
          <div className="flex gap-3 sm:gap-4 overflow-x-auto pb-4 scroll-smooth">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="shrink-0 w-72 sm:w-80 md:w-84 rounded-2xl bg-white p-4 sm:p-5 border border-slate-200 shadow-xs space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="h-5 w-20 rounded-md bg-slate-200" />
                  <div className="h-4 w-4 rounded bg-slate-200" />
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-full rounded bg-slate-200" />
                  <div className="h-4 w-3/4 rounded bg-slate-200" />
                </div>
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div className="h-3.5 w-28 rounded bg-slate-100" />
                  <div className="h-3.5 w-10 rounded bg-slate-100" />
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </main>
  );
}
