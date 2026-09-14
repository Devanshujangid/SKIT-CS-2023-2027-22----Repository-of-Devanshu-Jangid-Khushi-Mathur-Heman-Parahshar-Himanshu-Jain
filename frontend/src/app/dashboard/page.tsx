"use client";

import { useUser, UserButton } from "@clerk/nextjs";

export default function DashboardPage() {
  const { user } = useUser();

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-4xl rounded-2xl bg-white p-8 shadow-sm">
        <header className="flex items-center justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              Welcome, {user?.firstName || "Student"}! 👋
            </h1>
            <p className="mt-1 text-slate-600">Smart Learning Planner Dashboard</p>
          </div>
          <UserButton />
        </header>

        <section className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-xl border bg-blue-50 p-6">
            <h3 className="font-semibold text-blue-900">Profile Status</h3>
            <p className="mt-2 text-2xl font-bold text-blue-700">Completed ✅</p>
          </div>

          <div className="rounded-xl border bg-emerald-50 p-6">
            <h3 className="font-semibold text-emerald-900">Active Semester</h3>
            <p className="mt-2 text-2xl font-bold text-emerald-700">Configured</p>
          </div>

          <div className="rounded-xl border bg-purple-50 p-6">
            <h3 className="font-semibold text-purple-900">AI Planner</h3>
            <p className="mt-2 text-2xl font-bold text-purple-700">Ready</p>
          </div>
        </section>
      </div>
    </main>
  );
}
