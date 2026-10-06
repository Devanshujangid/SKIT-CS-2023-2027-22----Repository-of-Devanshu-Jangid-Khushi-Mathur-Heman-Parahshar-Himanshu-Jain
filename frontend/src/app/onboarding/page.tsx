"use client";

import { useState, useEffect } from "react";
import { useAuth, useUser, UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import { Sparkles, ArrowRight, BookOpen, Clock, Target, Loader2 } from "lucide-react";

export default function OnboardingPage() {
  const { getToken } = useAuth();
  const { user, isLoaded: isUserLoaded } = useUser();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  
  const [formData, setFormData] = useState({
    semester: "",
    study_hours_per_day: "",
    goals: "",
    subjects: "",
  });

  // Pre-populate form if user profile exists in localStorage
  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("slp_user_profile");
      if (savedProfile) {
        const parsed = JSON.parse(savedProfile);
        setFormData({
          semester: parsed.semester ? String(parsed.semester) : "",
          study_hours_per_day: parsed.study_hours_per_day ? String(parsed.study_hours_per_day) : "",
          goals: Array.isArray(parsed.goals) ? parsed.goals.join(", ") : (parsed.goals || ""),
          subjects: Array.isArray(parsed.subjects) ? parsed.subjects.join(", ") : (parsed.subjects || ""),
        });
      }
    } catch (e) {
      console.error("Failed to parse saved profile:", e);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || isGeneratingPlan) return;

    setIsSubmitting(true);
    setIsGeneratingPlan(true);

    const payload = {
      semester: parseInt(formData.semester) || 1,
      study_hours_per_day: parseFloat(formData.study_hours_per_day) || 4,
      goals: formData.goals,
      subjects: formData.subjects.split(",").map((s) => s.trim()).filter(Boolean),
    };

    // Store in localStorage immediately for seamless client-side state
    try {
      localStorage.setItem("slp_user_profile", JSON.stringify(payload));
    } catch (e) {
      console.error("LocalStorage save error:", e);
    }

    try {
      const token = await getToken();

      // 1. Save profile to backend /api/v1/profile
      const profileRes = await fetch(`${API_BASE_URL}/api/v1/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!profileRes.ok) {
        console.warn("Backend profile save API returned non-200, continuing with plan generation.");
      }

      // 2. Generate 7-Day Study Plan with Khushi's endpoint POST /api/v1/ai/generate-plan
      const aiRes = await fetch(`${API_BASE_URL}/api/v1/ai/generate-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          onboarding_data: {
            semester: payload.semester,
            study_hours_per_day: payload.study_hours_per_day,
            goals: payload.goals,
            subjects: payload.subjects,
          },
        }),
      });

      if (!aiRes.ok) {
        const errorText = await aiRes.text();
        let detail = `Server status ${aiRes.status}`;
        try {
          const parsed = JSON.parse(errorText);
          if (parsed.detail) detail = parsed.detail;
        } catch {
          if (errorText) detail = errorText;
        }
        throw new Error(detail);
      }

      const aiData = await aiRes.json();
      if (!aiData.success) {
        throw new Error("AI Plan Generation failed to return success status.");
      }

      // Poll generation status until backend background task finishes saving plan
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

      // Navigate to dashboard where fetchPlans() auto-loads the new plan
      router.push("/dashboard");
    } catch (error: any) {
      console.error("Error generating AI plan on onboarding submit:", error);
      const msg = error.message || "Failed to generate AI study plan. Please try again.";
      alert(`Error generating study plan: ${msg}`);
      setIsSubmitting(false);
      setIsGeneratingPlan(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 p-6 sm:p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        
        {/* Top Navbar with Clerk Session Indicator */}
        <div className="flex items-center justify-between rounded-2xl bg-white p-4 shadow-sm border border-slate-100">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            <span className="font-bold text-slate-900">Smart Learning Planner</span>
          </div>
          
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              Go to Dashboard
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            {isUserLoaded && <UserButton appearance={{ elements: { avatarBox: "h-9 w-9" } }} />}
          </div>
        </div>

        {/* Onboarding Form Card */}
        <div className="rounded-2xl bg-white p-8 shadow-sm border border-slate-100">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
              Welcome{user?.firstName ? `, ${user.firstName}` : ""}! Complete Your Profile 🚀
            </h1>
            <p className="mt-1 text-slate-600">
              Tell us about your semester, study targets, and subjects so Gemini AI can generate your custom schedule.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                  <span className="flex items-center gap-1.5">
                    <BookOpen className="h-4 w-4 text-indigo-600" />
                    Semester
                  </span>
                </label>
                <input
                  type="number"
                  name="semester"
                  required
                  min="1"
                  max="10"
                  disabled={isSubmitting || isGeneratingPlan}
                  value={formData.semester}
                  onChange={handleChange}
                  className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100"
                  placeholder="e.g., 5"
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                  <span className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-indigo-600" />
                    Daily Study Hours
                  </span>
                </label>
                <input
                  type="number"
                  step="0.5"
                  name="study_hours_per_day"
                  required
                  min="0.5"
                  max="18"
                  disabled={isSubmitting || isGeneratingPlan}
                  value={formData.study_hours_per_day}
                  onChange={handleChange}
                  className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100"
                  placeholder="e.g., 4.5"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <Target className="h-4 w-4 text-indigo-600" />
                  Academic & Career Goals
                </span>
              </label>
              <textarea
                name="goals"
                required
                disabled={isSubmitting || isGeneratingPlan}
                value={formData.goals}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100"
                placeholder="e.g., Maintain 9.0 CGPA and master backend microservices architecture"
                rows={3}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Subjects (comma-separated)
              </label>
              <input
                type="text"
                name="subjects"
                required
                disabled={isSubmitting || isGeneratingPlan}
                value={formData.subjects}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100"
                placeholder="Operating Systems, Computer Networks, Data Structures"
              />
            </div>

            <div className="mt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
              <button
                type="submit"
                disabled={isSubmitting || isGeneratingPlan}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-8 py-3 font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-md"
              >
                {isSubmitting || isGeneratingPlan ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Generating 7-Day Plan...</span>
                  </>
                ) : (
                  <>
                    Save Profile & Generate 7-Day Plan
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              <Link
                href="/dashboard"
                className="text-xs text-slate-500 hover:text-slate-800 underline underline-offset-4"
              >
                Skip to Dashboard →
              </Link>
            </div>
          </form>
        </div>

        {/* High Visibility Generating Plan Loading Modal Overlay */}
        {(isSubmitting || isGeneratingPlan) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
            <div className="flex max-w-md flex-col items-center rounded-2xl bg-white p-8 text-center shadow-2xl border border-slate-100">
              <div className="relative mb-4 flex items-center justify-center">
                <div className="absolute h-16 w-16 animate-ping rounded-full bg-indigo-100 opacity-75"></div>
                <div className="relative rounded-full bg-indigo-600 p-4 text-white shadow-lg">
                  <Sparkles className="h-8 w-8 animate-spin" />
                </div>
              </div>
              <h3 className="text-xl font-bold text-slate-900">Generating Your AI Study Plan</h3>
              <p className="mt-2 text-sm text-slate-600">
                Saving profile & prompting Gemini AI to craft your personalized 7-day academic schedule...
              </p>
              <div className="mt-6 flex items-center gap-2 rounded-xl bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-600 border border-indigo-100">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Redirecting to Dashboard once ready...</span>
              </div>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
