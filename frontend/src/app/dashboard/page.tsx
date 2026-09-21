"use client";

import { useUser, UserButton } from "@clerk/nextjs";
import { BookOpen, Clock, Target, Sparkles, CalendarX2 } from "lucide-react";

export default function DashboardPage() {
  const { user } = useUser();

  return (
    <main className="min-h-screen bg-slate-50 p-6 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* Header Section */}
        <header className="flex items-center justify-between rounded-2xl bg-white p-6 shadow-sm">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
              Welcome back, {user?.firstName || "Student"}! 👋
            </h1>
            <p className="mt-1 text-slate-600">Let's map out your academic success.</p>
          </div>
          <UserButton appearance={{ elements: { avatarBox: "h-12 w-12" } }} />
        </header>

        {/* Profile Summary Stat Bar */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={<BookOpen />} title="Active Semester" value="Pending" />
          <StatCard icon={<Clock />} title="Daily Target" value="-- hrs" />
          <StatCard icon={<Target />} title="Current Goal" value="Not set" />
          <StatCard icon={<BookOpen />} title="Enrolled Subjects" value="0" />
        </section>

        {/* Main Dashboard Grid */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          
          {/* Left Column: Empty Study Plan Hero CTA */}
          <div className="flex flex-col justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-700 p-8 text-white shadow-sm lg:col-span-2">
            <div className="max-w-lg">
              <h2 className="mb-4 text-3xl font-bold tracking-tight">Your study plan is empty.</h2>
              <p className="mb-8 text-indigo-100">
                Generate your first 7-day personalized academic schedule using Gemini AI. We will analyze your goals and available hours to build the perfect timetable.
              </p>
              <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 font-semibold text-indigo-600 transition-colors hover:bg-indigo-50">
                <Sparkles className="h-5 w-5" />
                Generate 7-Day Study Plan
              </button>
            </div>
          </div>

          {/* Right Column: Today's Schedule Empty State */}
          <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-8 text-center shadow-sm">
            <div className="mb-4 rounded-full bg-slate-100 p-4">
              <CalendarX2 className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">No tasks for today</h3>
            <p className="mt-2 text-sm text-slate-500">
              Generate your AI study plan to populate your daily schedule.
            </p>
          </div>
          
        </section>
      </div>
    </main>
  );
}

// Reusable Widget Component
function StatCard({ icon, title, value }: { icon: React.ReactNode; title: string; value: string }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl bg-white p-6 shadow-sm">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <p className="text-xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  );
}
