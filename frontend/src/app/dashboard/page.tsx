"use client";

import { useState, useEffect } from "react";
import { useUser, UserButton } from "@clerk/nextjs";
import { BookOpen, Clock, Target, Sparkles, CalendarX2, RefreshCw } from "lucide-react";

interface StatCardProps {
  icon?: React.ReactNode;
  title: string;
  value: string;
  subtitle?: string;
  isLoading?: boolean;
}

export default function DashboardPage() {
  const { user, isLoaded: isUserLoaded } = useUser();
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Simulate loading delay for skeleton preview
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  const toggleLoading = () => setIsLoading((prev) => !prev);

  if (isLoading || !isUserLoaded) {
    return <DashboardSkeleton onToggleLoading={toggleLoading} />;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* Testing / Preview Control */}
        <div className="flex justify-end">
          <button
            onClick={toggleLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Toggle Skeleton View
          </button>
        </div>

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
          <StatCard
            icon={<Clock className="h-6 w-6" />}
            title="Total Weekly Hours"
            value="28.5 hrs"
            subtitle="Target plan"
          />
          <StatCard
            icon={<Target className="h-6 w-6" />}
            title="Primary Focus"
            value="Data Structures"
            subtitle="High priority"
          />
          <StatCard
            icon={<BookOpen className="h-6 w-6" />}
            title="Active Semester"
            value="Semester 5"
            subtitle="Fall 2026"
          />
          <StatCard
            icon={<Sparkles className="h-6 w-6" />}
            title="Enrolled Subjects"
            value="6 Courses"
            subtitle="Current active"
          />
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
              <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 cursor-pointer">
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

// Reusable Widget Component with Skeleton State Support
function StatCard({ icon, title, value, subtitle, isLoading }: StatCardProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-4 rounded-2xl bg-white p-6 shadow-sm animate-pulse">
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
    <div className="flex items-center gap-4 rounded-2xl bg-white p-6 shadow-sm transition-all hover:shadow-md">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
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

        {/* Main Dashboard 2-Column Section Skeleton */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          
          {/* Left Column Skeleton (2-col) */}
          <div className="flex flex-col justify-between rounded-2xl bg-slate-200 p-8 shadow-sm lg:col-span-2 min-h-[260px]">
            <div className="space-y-4 max-w-lg">
              <div className="h-8 w-3/4 rounded-md bg-slate-300" />
              <div className="h-4 w-full rounded-md bg-slate-300" />
              <div className="h-4 w-5/6 rounded-md bg-slate-300" />
            </div>
            <div className="h-12 w-52 rounded-lg bg-slate-300 mt-6" />
          </div>

          {/* Right Column Skeleton (1-col) */}
          <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-8 text-center shadow-sm min-h-[260px] space-y-4">
            <div className="h-16 w-16 rounded-full bg-slate-200" />
            <div className="h-5 w-36 rounded-md bg-slate-200" />
            <div className="h-4 w-48 rounded-md bg-slate-200" />
          </div>

        </section>
      </div>
    </main>
  );
}

