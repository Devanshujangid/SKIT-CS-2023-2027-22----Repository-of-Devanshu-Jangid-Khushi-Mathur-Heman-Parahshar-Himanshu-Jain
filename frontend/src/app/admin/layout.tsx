"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, useUser } from "@clerk/nextjs";
import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  BookOpen,
  History,
  Settings,
  ArrowLeft,
  Sparkles,
  Menu,
  X,
  Database,
  Cpu,
  Wifi,
  CheckCircle2,
} from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user } = useUser();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const adminNavItems = [
    {
      name: "System Overview",
      href: "/admin",
      icon: LayoutDashboard,
      active: pathname === "/admin",
    },
    {
      name: "Student Roster",
      href: "/admin#students",
      icon: Users,
      active: false,
    },
    {
      name: "Diagnostic Telemetry",
      href: "/admin#diagnostics",
      icon: ShieldAlert,
      active: false,
    },
    {
      name: "Coursera Vector Catalog",
      href: "/admin#catalog",
      icon: BookOpen,
      active: false,
    },
    {
      name: "Plan Versions & RLS",
      href: "/admin#audit",
      icon: History,
      active: false,
    },
    {
      name: "Admin Settings",
      href: "/admin#settings",
      icon: Settings,
      active: false,
    },
  ];

  return (
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-64 flex-col justify-between border-r border-slate-800 bg-slate-950 p-5 shrink-0">
        <div className="space-y-6">
          
          {/* Logo & Institution Header */}
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-600/30">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <span className="font-extrabold text-sm tracking-tight text-white block">
                  Smart Planner
                </span>
                <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-indigo-400 block">
                  Faculty & Admin Console
                </span>
              </div>
            </div>
            <div className="pt-2">
              <span className="inline-block text-[11px] font-medium text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                SKIT CSE • Dept Portal
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 pt-2">
            <p className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Management
            </p>
            {adminNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all ${
                    item.active
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                      : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Live System Telemetry Status Pill */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3.5 space-y-2 text-xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Live Architecture
            </span>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                FastAPI /api/v1
              </span>
              <span className="text-emerald-400 font-mono">200 OK</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Database className="h-3 w-3 text-indigo-400" />
                Supabase RLS
              </span>
              <span className="text-indigo-300 font-mono">Active</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="h-3 w-3 text-purple-400" />
                Gemini 3.6 Flash
              </span>
              <span className="text-purple-300 font-mono">Ready</span>
            </div>
          </div>
        </div>

        {/* Back to Student Dashboard Button */}
        <div className="pt-4 border-t border-slate-800 space-y-3">
          <Link
            href="/dashboard"
            className="flex items-center justify-center gap-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Student Dashboard</span>
          </Link>

          <div className="flex items-center justify-between px-2 pt-1 text-[11px] text-slate-500">
            <span>Admin Auth Mode</span>
            <span className="font-mono text-emerald-500 font-semibold">Active</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Header Bar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/70 px-4 sm:px-6 backdrop-blur-md sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg bg-slate-900 text-slate-400 hover:text-white"
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <div>
              <h1 className="text-sm sm:text-base font-bold text-white tracking-tight flex items-center gap-2">
                <span>SKIT Academic Administration Console</span>
                <span className="hidden sm:inline-block rounded-md bg-indigo-950 border border-indigo-700/50 px-2 py-0.5 text-[10px] font-bold text-indigo-300">
                  50% Checkpoint Defense
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/analytics"
              className="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              <span>View Analytics</span>
            </Link>

            <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
              <span className="text-xs font-medium text-slate-300 hidden sm:inline-block">
                {user?.fullName || "Faculty Admin"}
              </span>
              <UserButton />
            </div>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {isMobileMenuOpen && (
          <div className="lg:hidden border-b border-slate-800 bg-slate-950 p-4 space-y-2">
            {adminNavItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-900"
              >
                <item.icon className="h-4 w-4" />
                <span>{item.name}</span>
              </Link>
            ))}
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white mt-2"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Return to Dashboard</span>
            </Link>
          </div>
        )}

        {/* Page Children */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {children}
        </main>
      </div>

    </div>
  );
}
