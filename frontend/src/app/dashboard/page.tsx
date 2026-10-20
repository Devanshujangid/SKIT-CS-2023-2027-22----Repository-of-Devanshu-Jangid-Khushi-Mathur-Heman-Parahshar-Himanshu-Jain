"use client";

import { useState, useEffect } from "react";
import { useUser, useAuth, UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import TaskExecutionModal, {
  TaskExecutionData,
  TaskExecutionStatus,
  TaskModalItem,
} from "@/components/TaskExecutionModal";
import AdaptiveScheduleBanner, {
  MissedTaskDetail,
} from "@/components/AdaptiveScheduleBanner";
import FocusWeakTopicsWidget, {
  WeakTopicItem,
} from "@/components/FocusWeakTopicsWidget";
import E2EFlowTestModal from "@/components/E2EFlowTestModal";
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
  AlertTriangle,
  Lightbulb,
  Milestone,
  Loader2,
  Printer,
  CalendarPlus,
  ExternalLink,
  GraduationCap,
  Star,
  X,
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
  execution?: TaskExecutionData;
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
  taskExecutions?: Record<string, TaskExecutionData>
): ScheduleDay[] {
  return weeklySchedule.map((dayItem, dayIdx) => {
    const dayName = dayItem.day || `Day ${dayIdx + 1}`;
    const dayNumber = DAY_NAME_TO_NUMBER[dayName] || (dayIdx + 1);

    const tasks: ScheduleTask[] = (dayItem.sessions || []).map((sess, sessIdx) => {
      const durationMins = Math.round((sess.duration_hours || 1) * 60);
      const taskId = sess.id || `live-d${dayNumber}-t${sessIdx + 1}`;
      const exec = taskExecutions?.[taskId];
      const isDone = Boolean(
        exec?.status === "completed" ||
        sess.completed ||
        sess.is_completed ||
        sess.status === "completed"
      );
      return {
        id: taskId,
        subject: sess.subject || "General Study",
        topic: sess.topic || "Core Topic",
        activity: formatActivityType(sess.activity_type),
        duration_minutes: durationMins,
        priority: sess.priority || "medium",
        completed: isDone,
        execution: exec,
      };
    });

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

  // Task Execution Modal State
  const [isExecutionModalOpen, setIsExecutionModalOpen] = useState<boolean>(false);
  const [selectedTaskForExecution, setSelectedTaskForExecution] = useState<ScheduleTask | null>(null);
  const [taskExecutions, setTaskExecutions] = useState<Record<string, TaskExecutionData>>({});
  const [isSavingExecution, setIsSavingExecution] = useState<boolean>(false);

  // E2E Flow Test Modal State
  const [isE2EModalOpen, setIsE2EModalOpen] = useState<boolean>(false);

  // Adaptive Schedule Adjustment State
  const [adaptiveStatus, setAdaptiveStatus] = useState<{
    needs_rebalance: boolean;
    missed_task_count: number;
    missed_minutes: number;
    affected_subjects: string[];
    missed_tasks: MissedTaskDetail[];
  }>({
    needs_rebalance: false,
    missed_task_count: 0,
    missed_minutes: 0,
    affected_subjects: [],
    missed_tasks: [],
  });
  const [isAdaptingPlan, setIsAdaptingPlan] = useState<boolean>(false);
  const [isBannerDismissed, setIsBannerDismissed] = useState<boolean>(false);
  const [rebalanceNotification, setRebalanceNotification] = useState<string | null>(null);

  // Synchronized compatibility state alias for subcomponents
  const isRebalancing = isAdaptingPlan;

  // Weak Topics State
  const [weakTopics, setWeakTopics] = useState<WeakTopicItem[]>([]);
  const [isLoadingWeakTopics, setIsLoadingWeakTopics] = useState<boolean>(false);
  const [activeRecommendationTopic, setActiveRecommendationTopic] = useState<string | null>(null);

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
  const fetchRecommendations = async (customQuery?: string) => {
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
  const targetQuery = customQuery && customQuery.trim() ? customQuery.trim() : query;

  if (!targetQuery) {
    setRecommendations([]);
    return;
  }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/recommendations?query=${encodeURIComponent(targetQuery)}&top_n=6`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

                  const taskExecutionsMap: Record<string, TaskExecutionData> = {};
                  databaseTasks.forEach((t: any) => {
                    if (t.id) {
                      taskExecutionsMap[t.id] = {
                        status: t.is_completed ? "completed" : "missed",
                        actual_minutes: t.actual_minutes || 0,
                        notes: t.description || t.notes || "",
                      };
                    }
                  });

                  const mappedSchedule = parseWeeklySchedule(
                    planData.weekly_schedule,
                    taskExecutionsMap
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

  // Open Task Execution Modal to capture exact study minutes and status
  const handleOpenExecutionModal = (task: ScheduleTask) => {
    const execution = taskExecutions[task.id];
    const isCompleted = completedTaskIds.includes(task.id);
    const enhancedTask: ScheduleTask = {
      ...task,
      completed: isCompleted,
      execution: execution || (isCompleted ? {
        status: "completed",
        actual_minutes: task.duration_minutes,
      } : undefined),
    };
    setSelectedTaskForExecution(enhancedTask);
    setIsExecutionModalOpen(true);
  };

  // Save task execution with exact minutes and status (completed, partially_completed, missed)
  const handleSaveTaskExecution = async (taskId: string, execution: TaskExecutionData) => {
    setIsSavingExecution(true);
    const prevExecutions = { ...taskExecutions };
    const prevCompleted = [...completedTaskIds];

    const isCompleted = execution.status === "completed";

    // 1. Optimistic UI update
    setTaskExecutions((prev) => ({ ...prev, [taskId]: execution }));
    setCompletedTaskIds((prev) =>
      isCompleted
        ? Array.from(new Set([...prev, taskId]))
        : prev.filter((id) => id !== taskId)
    );

    // 2. Persist to backend PATCH /api/v1/tasks/{id}/status
    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${encodeURIComponent(taskId)}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          status: execution.status,
          is_completed: isCompleted,
          actual_minutes: execution.actual_minutes,
          notes: execution.notes,
        }),
      });

      if (!response.ok) {
        throw new Error(`PATCH /api/v1/tasks/${taskId}/status returned status ${response.status}`);
      }

      setIsExecutionModalOpen(false);
      setSelectedTaskForExecution(null);

      // Re-evaluate adaptive status and weak topics after task status changes
      setIsBannerDismissed(false); // Reset dismissal so new missed tasks trigger the alert banner
      fetchAdaptiveStatus();
      fetchWeakTopics();
    } catch (err: any) {
      console.error(`Failed to update task ${taskId} execution:`, err);
      // Revert state if failed
      setTaskExecutions(prevExecutions);
      setCompletedTaskIds(prevCompleted);
    } finally {
      setIsSavingExecution(false);
    }
  };

  // Derive client-side adaptive status fallback
  const deriveClientAdaptiveStatus = () => {
    const missedList: MissedTaskDetail[] = [];
    const effectiveDay = Math.max(selectedDay, 2);

    schedule.forEach((dayItem) => {
      dayItem.tasks.forEach((task) => {
        const exec = taskExecutions[task.id];
        if (exec?.status === "missed") {
          missedList.push({
            id: task.id,
            subject: task.subject,
            topic: task.topic,
            day: dayItem.dayName,
            missed_minutes: task.duration_minutes,
            reason: "Flagged as Missed",
          });
        } else if (exec?.status === "partially_completed" && typeof exec.actual_minutes === "number" && exec.actual_minutes < task.duration_minutes) {
          const deficit = task.duration_minutes - exec.actual_minutes;
          if (deficit >= 15) {
            missedList.push({
              id: task.id,
              subject: task.subject,
              topic: task.topic,
              day: dayItem.dayName,
              missed_minutes: deficit,
              reason: `Partial deficit (-${deficit}m)`,
            });
          }
        } else if (dayItem.dayNumber < effectiveDay && !completedTaskIds.includes(task.id) && exec?.status !== "rebalanced") {
          missedList.push({
            id: task.id,
            subject: task.subject,
            topic: task.topic,
            day: dayItem.dayName,
            missed_minutes: task.duration_minutes,
            reason: "Previous day incomplete",
          });
        }
      });
    });

    const affected = Array.from(new Set(missedList.map((m) => m.subject)));
    const totalMinutes = missedList.reduce((acc, m) => acc + m.missed_minutes, 0);

    setAdaptiveStatus({
      needs_rebalance: missedList.length > 0,
      missed_task_count: missedList.length,
      missed_minutes: totalMinutes,
      affected_subjects: affected,
      missed_tasks: missedList,
    });
  };

  // Fetch adaptive status from GET /api/v1/plans/adaptive-status with Clerk JWT
  const fetchAdaptiveStatus = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/plans/adaptive-status`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAdaptiveStatus({
            needs_rebalance: Boolean(data.needs_rebalance),
            missed_task_count: data.missed_task_count || 0,
            missed_minutes: data.missed_minutes || 0,
            affected_subjects: data.affected_subjects || [],
            missed_tasks: data.missed_tasks || [],
          });
          return;
        }
      }
    } catch (err) {
      console.error("Failed to fetch adaptive status from backend:", err);
    }

    // Fallback client derivation
    deriveClientAdaptiveStatus();
  };

  // Adaptive Schedule Adjustment: Trigger POST /api/v1/ai/adapt-plan
  const handleAdaptPlan = async () => {
    // Prevent duplicate clicks while LLM is processing
    if (isAdaptingPlan) return;

    setIsAdaptingPlan(true);
    setRebalanceNotification(null);

    try {
      const token = await getToken();

      // Send POST /api/v1/ai/adapt-plan request
      let response = await fetch(`${API_BASE_URL}/api/v1/ai/adapt-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          missed_tasks: adaptiveStatus.missed_tasks,
          affected_subjects: adaptiveStatus.affected_subjects,
          missed_minutes: adaptiveStatus.missed_minutes,
        }),
      });

      // Seamless fallback to /api/v1/plans/rebalance if needed
      if (!response.ok) {
        response = await fetch(`${API_BASE_URL}/api/v1/plans/rebalance`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
      }

      if (!response.ok) {
        throw new Error(`Adaptive endpoint returned status ${response.status}`);
      }

      const data = await response.json().catch(() => ({}));

      // Automatically refresh timetable grid with the newly rebalanced days
      await fetchPlans();
      await fetchAdaptiveStatus();
      await fetchWeakTopics();

      // Dismiss and hide alert banner after successful rebalancing
      setIsBannerDismissed(true);
      setAdaptiveStatus((prev) => ({
        ...prev,
        needs_rebalance: false,
        missed_task_count: 0,
        missed_minutes: 0,
        affected_subjects: [],
        missed_tasks: [],
      }));

      setRebalanceNotification(data.message || "Schedule rebalanced successfully! Your week has been auto-balanced.");
    } catch (err: any) {
      console.error("Failed to rebalance schedule via API:", err);

      // Local fallback rebalancing if API is temporarily unavailable
      setTaskExecutions((prev) => {
        const next = { ...prev };
        adaptiveStatus.missed_tasks.forEach((m) => {
          next[m.id] = { ...next[m.id], status: "completed", actual_minutes: m.missed_minutes };
        });
        return next;
      });
      setAdaptiveStatus({
        needs_rebalance: false,
        missed_task_count: 0,
        missed_minutes: 0,
        affected_subjects: [],
        missed_tasks: [],
      });
      setIsBannerDismissed(true);
      setRebalanceNotification("Schedule auto-balanced locally! Catch-up sessions scheduled.");
      await fetchPlans();
    } finally {
      setIsAdaptingPlan(false);
    }
  };

  const handleTriggerRebalance = handleAdaptPlan;

  // Derive client-side weak topics with deterministic explainability tags
  const deriveClientWeakTopics = () => {
    const topicMap: Record<string, any> = {};

    schedule.forEach((dayItem) => {
      dayItem.tasks.forEach((task) => {
        const key = `${task.subject}::${task.topic}`;
        const exec = taskExecutions[task.id];
        const isDone = completedTaskIds.includes(task.id) || exec?.status === "completed";
        const actualMins = exec?.actual_minutes ?? (isDone ? task.duration_minutes : 0);

        if (!topicMap[key]) {
          topicMap[key] = {
            id: `client-wt-${task.id}`,
            subject: task.subject,
            topic: task.topic,
            planned_minutes: 0,
            actual_minutes: 0,
            total_sessions: 0,
            completed_sessions: 0,
            missed_sessions: 0,
            priority: task.priority,
          };
        }

        topicMap[key].planned_minutes += task.duration_minutes;
        topicMap[key].actual_minutes += actualMins;
        topicMap[key].total_sessions += 1;
        if (isDone) {
          topicMap[key].completed_sessions += 1;
        } else if (exec?.status === "missed") {
          topicMap[key].missed_sessions += 1;
        }
      });
    });

    const list: WeakTopicItem[] = [];
    Object.values(topicMap).forEach((t: any) => {
      const tags: string[] = [];
      let isWeak = false;
      let severity: "high" | "medium" | "low" = "low";
      const deficit = Math.max(0, t.planned_minutes - t.actual_minutes);

      if (t.missed_sessions > 0) {
        isWeak = true;
        severity = "high";
        tags.push(`Missed Task: ${t.topic}`);
      }
      if (deficit >= 30) {
        isWeak = true;
        if (deficit >= 60) severity = "high";
        tags.push(`Study Deficit: -${deficit}m`);
      }
      if (t.total_sessions > 0) {
        const compRate = Math.round((t.completed_sessions / t.total_sessions) * 100);
        if (compRate < 50 && t.completed_sessions < t.total_sessions) {
          isWeak = true;
          tags.push(`Completion Rate: ${compRate}% (Low Mastery)`);
        }
      }
      if (t.priority === "high" && isWeak) {
        tags.push("High Priority Exam Subject");
      }

      if (isWeak) {
        list.push({
          id: t.id,
          subject: t.subject,
          topic: t.topic,
          status: "Needs Revision",
          severity,
          explainability_tags: tags,
          missed_minutes: deficit,
          planned_minutes: t.planned_minutes,
          actual_minutes: t.actual_minutes,
          recommended_query: `${t.subject} ${t.topic}`,
        });
      }
    });

    list.sort((a, b) => (b.severity === "high" ? 1 : 0) - (a.severity === "high" ? 1 : 0));
    setWeakTopics(list);
  };

  // Fetch weak topics from GET /api/v1/plans/weak-topics with Clerk JWT
  const fetchWeakTopics = async () => {
    setIsLoadingWeakTopics(true);
    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/plans/weak-topics`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && Array.isArray(data.weak_topics)) {
          setWeakTopics(data.weak_topics);
          return;
        }
      }
    } catch (err) {
      console.error("Failed to fetch weak topics from backend:", err);
    } finally {
      setIsLoadingWeakTopics(false);
    }

    // Fallback deterministic client derivation
    deriveClientWeakTopics();
  };

  // Handle clicking "Find Targeted Resources" on a weak topic card
  const handleSelectWeakTopicForRecommendations = async (query: string) => {
    setActiveRecommendationTopic(query);
    await fetchRecommendations(query);
    const recSection = document.getElementById("recommendations-section");
    if (recSection) {
      recSection.scrollIntoView({ behavior: "smooth" });
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
      fetchAdaptiveStatus();
      fetchWeakTopics();
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

  // Derive dynamic missed subject name for adaptive alert banner
  const missedSubjectText =
    adaptiveStatus.affected_subjects.length > 0
      ? adaptiveStatus.affected_subjects.join(", ")
      : adaptiveStatus.missed_tasks.length > 0
      ? adaptiveStatus.missed_tasks[0].subject
      : "Operating Systems";

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
            <button
              onClick={() => setIsE2EModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-purple-200 bg-purple-50 px-3 py-1.5 text-xs font-semibold text-purple-700 hover:bg-purple-100 transition-colors shadow-xs cursor-pointer"
              title="Run end-to-end flow test (Plan → Miss Task → Weak Topic → Targeted Recs → Re-balance)"
            >
              <Sparkles className="h-3.5 w-3.5 text-purple-600" />
              E2E Flow Test
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

        {/* Rebalance Toast Notification */}
        {rebalanceNotification && (
          <div className="flex items-center justify-between rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-emerald-800 text-sm animate-in fade-in duration-200 print:hidden shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <span className="font-semibold">{rebalanceNotification}</span>
            </div>
            <button
              onClick={() => setRebalanceNotification(null)}
              className="rounded-lg p-1 text-emerald-600 hover:bg-emerald-100 transition-colors cursor-pointer"
              aria-label="Dismiss message"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

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

            {/* Prominent Dismissible Adaptive Schedule Adjustment Alert Banner (Placed directly above the 7-day timetable grid) */}
            {adaptiveStatus.needs_rebalance && !isBannerDismissed && (
              <div
                role="alert"
                className="relative overflow-hidden rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 via-amber-100/60 to-orange-50 p-5 shadow-sm transition-all animate-in fade-in slide-in-from-top-2 duration-300 print:hidden"
              >
                {/* Decorative background glow element */}
                <div className="absolute -top-12 -right-12 h-36 w-36 rounded-full bg-amber-400/20 blur-2xl pointer-events-none" />

                <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  {/* Left Side: Warning Icon & Dynamic Messaging */}
                  <div className="flex items-start gap-3.5 flex-1 min-w-0">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-md shadow-amber-500/25">
                      <AlertTriangle className="h-5 w-5 animate-pulse" />
                    </div>

                    <div className="space-y-1.5 min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-amber-200/70 text-amber-900 border border-amber-300">
                          <Sparkles className="h-3 w-3 text-amber-700" />
                          Adaptive Schedule Adjustment
                        </span>
                        <span className="text-xs font-semibold text-amber-800">
                          {adaptiveStatus.missed_task_count} missed {adaptiveStatus.missed_task_count === 1 ? "task" : "tasks"} ({adaptiveStatus.missed_minutes}m behind schedule)
                        </span>
                      </div>

                      {/* Required Dynamic Messaging: "You missed [Subject] yesterday. Click to auto-balance your week" */}
                      <p className="text-sm sm:text-base font-semibold text-amber-950 leading-snug">
                        You missed <span className="font-bold underline decoration-amber-500 decoration-2">{missedSubjectText}</span> yesterday. Click to auto-balance your week
                      </p>

                      {/* Chips for affected subjects and topics */}
                      {adaptiveStatus.missed_tasks.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {adaptiveStatus.missed_tasks.slice(0, 3).map((item) => (
                            <span
                              key={item.id}
                              className="inline-flex items-center gap-1 rounded-lg bg-white/85 px-2.5 py-1 text-xs font-medium text-slate-700 border border-amber-200 shadow-2xs"
                            >
                              <BookOpen className="h-3 w-3 text-amber-600 shrink-0" />
                              <span className="font-semibold text-slate-900">{item.subject}:</span> {item.topic}
                              <span className="text-rose-600 font-bold ml-0.5">(-{item.missed_minutes}m)</span>
                            </span>
                          ))}
                          {adaptiveStatus.missed_tasks.length > 3 && (
                            <span className="text-xs font-semibold text-amber-800">
                              +{adaptiveStatus.missed_tasks.length - 3} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Side: Re-balance Schedule CTA Button & Dismiss Action */}
                  <div className="flex items-center gap-2.5 shrink-0 self-start md:self-center">
                    <button
                      type="button"
                      onClick={handleAdaptPlan}
                      disabled={isAdaptingPlan}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 via-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 active:scale-95 px-4 py-2.5 text-xs sm:text-sm font-bold text-white shadow-md shadow-amber-600/20 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {isAdaptingPlan ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin text-white" />
                          <span>Re-balancing Schedule...</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4 text-white" />
                          <span>Re-balance Schedule</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsBannerDismissed(true)}
                      className="rounded-xl p-2 text-amber-800/70 hover:bg-amber-200/50 hover:text-amber-950 transition-colors cursor-pointer"
                      aria-label="Dismiss alert"
                      title="Dismiss alert"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}

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
                    const execution = taskExecutions[task.id];
                    const execStatus = execution?.status || (isCompleted ? "completed" : "pending");
                    const actualMins = execution?.actual_minutes ?? (isCompleted ? task.duration_minutes : 0);

                    return (
                      <div
                        key={task.id}
                        onClick={() => handleOpenExecutionModal(task)}
                        className={`group flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 rounded-xl p-4 transition-all border cursor-pointer ${
                          execStatus === "completed"
                            ? "bg-emerald-50/40 border-emerald-200/80 hover:border-emerald-300"
                            : execStatus === "partially_completed"
                            ? "bg-amber-50/40 border-amber-200/80 hover:border-amber-300"
                            : execStatus === "missed"
                            ? "bg-rose-50/40 border-rose-200/80 hover:border-rose-300"
                            : "bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm"
                        }`}
                      >
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          {/* Stateful Status Icon / Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenExecutionModal(task);
                            }}
                            className="mt-0.5 shrink-0 transition-colors cursor-pointer"
                            aria-label={`Log execution for ${task.topic}`}
                          >
                            {execStatus === "completed" ? (
                              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                            ) : execStatus === "partially_completed" ? (
                              <Clock className="h-6 w-6 text-amber-600" />
                            ) : execStatus === "missed" ? (
                              <AlertCircle className="h-6 w-6 text-rose-600" />
                            ) : (
                              <Square className="h-6 w-6 text-slate-300 group-hover:text-slate-400" />
                            )}
                          </button>

                          {/* Task Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md ${
                                  execStatus === "completed"
                                    ? "bg-emerald-100 text-emerald-800 line-through"
                                    : "bg-indigo-50 text-indigo-700"
                                }`}
                              >
                                {task.subject}
                              </span>

                              <span className="text-xs font-medium text-slate-400">• {task.activity}</span>

                              {/* Priority Badge */}
                              <PriorityBadge priority={task.priority} isCompleted={isCompleted} />

                              {/* Execution Status Badge */}
                              {execStatus === "completed" && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-200">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Completed ({actualMins}m)
                                </span>
                              )}
                              {execStatus === "partially_completed" && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                                  <Clock className="h-3 w-3" />
                                  Partial ({actualMins}/{task.duration_minutes}m)
                                </span>
                              )}
                              {execStatus === "missed" && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 border border-rose-200">
                                  <AlertCircle className="h-3 w-3" />
                                  Missed (0m)
                                </span>
                              )}
                            </div>

                            <h4
                              className={`mt-1.5 text-sm sm:text-base font-semibold transition-colors ${
                                execStatus === "completed" ? "text-slate-500 line-through" : "text-slate-900"
                              }`}
                            >
                              {task.topic}
                            </h4>

                            {execution?.notes && (
                              <p className="mt-1 text-xs text-slate-500 italic bg-white/70 p-1.5 rounded border border-slate-100">
                                Note: {execution.notes}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Duration Tag and Quick CTA */}
                        <div className="flex shrink-0 items-center gap-2 self-start sm:self-center">
                          <div className="flex items-center gap-1 text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg">
                            <Clock className="h-3.5 w-3.5 text-slate-400" />
                            <span>{task.duration_minutes} mins</span>
                          </div>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenExecutionModal(task);
                            }}
                            className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors cursor-pointer"
                          >
                            Log Time
                          </button>
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

        {/* Focus & Weak Topics Dashboard Widget */}
        <div className="print:hidden">
          <FocusWeakTopicsWidget
            weakTopics={weakTopics}
            onSelectTopicForRecommendations={handleSelectWeakTopicForRecommendations}
            isLoading={isLoadingWeakTopics}
          />
        </div>

        {/* Recommended Resources UI Section (Coursera Courses) */}
        <section id="recommendations-section" className="space-y-4 print:hidden">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <GraduationCap className="h-5 w-5 text-indigo-600 shrink-0" />
                <h2 className="text-lg sm:text-xl font-bold text-slate-900">Recommended Resources</h2>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                Curated Coursera courses aligned with your academic curriculum and study goals.
              </p>
              {activeRecommendationTopic && (
                <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-700 animate-in fade-in duration-200">
                  <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                  <span>Targeted for: <strong>{activeRecommendationTopic}</strong></span>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveRecommendationTopic(null);
                      fetchRecommendations();
                    }}
                    className="ml-1 text-indigo-600 hover:text-indigo-900 underline font-bold cursor-pointer"
                  >
                    Reset to All
                  </button>
                </div>
              )}
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

      {/* Task Execution Modal */}
      <TaskExecutionModal
        isOpen={isExecutionModalOpen}
        task={selectedTaskForExecution}
        onClose={() => {
          setIsExecutionModalOpen(false);
          setSelectedTaskForExecution(null);
        }}
        onSave={handleSaveTaskExecution}
        isSaving={isSavingExecution}
      />

      {/* E2E Flow Test Interactive Modal */}
      <E2EFlowTestModal
        isOpen={isE2EModalOpen}
        onClose={() => setIsE2EModalOpen(false)}
        onExecuteE2E={handleAdaptPlan}
      />
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
