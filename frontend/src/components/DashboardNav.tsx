"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  CalendarDays, 
  BarChart3, 
  Settings, 
  ShieldCheck, 
  ArrowLeft,
  Sparkles
} from "lucide-react";

interface DashboardNavProps {
  showBackToDashboard?: boolean;
}

export default function DashboardNav({ showBackToDashboard = false }: DashboardNavProps) {
  const pathname = usePathname();

  const navItems = [
    {
      name: "Study Timetable",
      href: "/dashboard",
      icon: CalendarDays,
      active: pathname === "/dashboard",
      badge: null,
    },
    {
      name: "Academic Analytics",
      href: "/dashboard/analytics",
      icon: BarChart3,
      active: pathname.startsWith("/dashboard/analytics"),
      badge: "Module 8",
    },
    {
      name: "Profile & Settings",
      href: "/dashboard/settings",
      icon: Settings,
      active: pathname.startsWith("/dashboard/settings"),
      badge: "Module 11",
    },
    {
      name: "Admin Portal",
      href: "/admin",
      icon: ShieldCheck,
      active: pathname.startsWith("/admin"),
      badge: "Faculty / Admin",
    },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white/80 backdrop-blur-md px-4 py-3 rounded-2xl shadow-xs print:hidden mb-6">
      <div className="flex items-center gap-2">
        {showBackToDashboard && (
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-indigo-600 transition-colors shadow-2xs mr-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Dashboard</span>
          </Link>
        )}
        <div className="hidden sm:flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider pr-3 border-r border-slate-200">
          <Sparkles className="h-4 w-4 text-indigo-600" />
          <span>Smart Learning</span>
        </div>
        <nav className="flex items-center gap-1 sm:gap-2 overflow-x-auto py-0.5 max-w-full scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.active;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-white" : "text-slate-500"}`} />
                <span className="font-semibold">{item.name}</span>
                {item.badge && (
                  <span
                    className={`hidden md:inline-block rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      isActive
                        ? "bg-indigo-700/60 text-indigo-100"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          SKIT CSE • 2026-27
        </span>
      </div>
    </div>
  );
}
