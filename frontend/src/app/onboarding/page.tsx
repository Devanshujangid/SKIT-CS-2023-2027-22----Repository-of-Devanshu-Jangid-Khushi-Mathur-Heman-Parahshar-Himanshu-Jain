"use client";

import { useState, useEffect } from "react";
import { useAuth, useUser, UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import { Sparkles, ArrowRight, BookOpen, Clock, Target, CheckCircle2 } from "lucide-react";

export default function OnboardingPage() {
  const { getToken } = useAuth();
  const { user, isLoaded: isUserLoaded } = useUser();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
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
    setIsSubmitting(true);

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

      const response = await fetch(`${API_BASE_URL}/api/v1/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        console.warn("Backend profile save API returned non-200, continuing with local profile.");
      }
    } catch (error) {
      console.error("Error submitting profile to backend API:", error);
    } finally {
      setIsSubmitting(false);
      // Seamless navigation to dashboard
      router.push("/dashboard");
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
                  value={formData.semester}
                  onChange={handleChange}
                  className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
                  value={formData.study_hours_per_day}
                  onChange={handleChange}
                  className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
                value={formData.goals}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
                value={formData.subjects}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-200 p-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="Operating Systems, Computer Networks, Data Structures"
              />
            </div>

            <div className="mt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-8 py-3 font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50 cursor-pointer shadow-md"
              >
                {isSubmitting ? (
                  "Saving Profile..."
                ) : (
                  <>
                    Save Profile & Go to Dashboard
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

      </div>
    </main>
  );
}