"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { 
  CalendarDays, 
  BarChart3, 
  Settings, 
  ShieldCheck, 
  ArrowLeft,
  Sparkles,
  Bell,
  MessageSquare,
  CheckCheck,
  AlertTriangle,
  Calendar,
  BookOpen,
  ArrowRight,
  X
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import AiAssistantDrawer from "@/components/AiAssistantDrawer";

interface DashboardNavProps {
  showBackToDashboard?: boolean;
}

export interface NotificationItem {
  id: string;
  type: "exam" | "weak_topic" | "adaptive" | "course";
  title: string;
  description: string;
  time: string;
  is_read: boolean;
}

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-1",
    type: "exam",
    title: "Upcoming Mid-Term Exam",
    description: "Operating Systems (Units 1-3) on Nov 5, 2026. 4 days remaining to target process synchronization.",
    time: "15m ago",
    is_read: false,
  },
  {
    id: "notif-2",
    type: "weak_topic",
    title: "Unresolved Weak Topic",
    description: "Process Synchronization flagged as 'Needs Revision' (Study deficit: -90m, Sub-50% duration).",
    time: "1h ago",
    is_read: false,
  },
  {
    id: "notif-3",
    type: "adaptive",
    title: "Schedule Re-balanced",
    description: "Catch-up session placed on Wednesday 18:00 without exceeding 4.5h daily hours ceiling.",
    time: "3h ago",
    is_read: true,
  },
  {
    id: "notif-4",
    type: "course",
    title: "New Coursera Recommendation",
    description: "Matched 'Operating Systems and You' (Google / Coursera) with 0.46 similarity score.",
    time: "1d ago",
    is_read: true,
  },
];

export default function DashboardNav({ showBackToDashboard = false }: DashboardNavProps) {
  const pathname = usePathname();
  const { getToken } = useAuth();
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);
  const notificationRef = useRef<HTMLDivElement>(null);

  // Unread badge counter: Count alerts where is_read is false
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // Live Notifications: Fetch data from GET /api/v1/notifications on mount
  const fetchLiveNotifications = useCallback(async () => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/notifications`, {
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        const rawList = Array.isArray(data.notifications) 
          ? data.notifications 
          : (Array.isArray(data) ? data : []);

        if (rawList.length > 0) {
          interface RawNotificationPayload {
            id?: string;
            type?: "exam" | "weak_topic" | "adaptive" | "course";
            title?: string;
            description?: string;
            message?: string;
            time?: string;
            is_read?: boolean;
            unread?: boolean;
          }

          setNotifications(
            rawList.map((item: RawNotificationPayload, idx: number) => ({
              id: item.id || `notif-live-${idx}`,
              type: item.type || "exam",
              title: item.title || "Academic Notification",
              description: item.description || item.message || "",
              time: item.time || "Just now",
              is_read: typeof item.is_read === "boolean" 
                ? item.is_read 
                : (typeof item.unread === "boolean" ? !item.unread : false),
            }))
          );
        }
      }
    } catch (err) {
      console.warn("Could not fetch live notifications, retaining local telemetry:", err);
    }
  }, [getToken]);

  useEffect(() => {
    fetchLiveNotifications();
  }, [fetchLiveNotifications]);

  // Close notifications dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsNotificationsOpen(false);
      }
    };

    if (isNotificationsOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isNotificationsOpen]);

  const markAllAsRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      await fetch(`${API_BASE_URL}/api/v1/notifications/mark-all-read`, {
        method: "POST",
        headers,
      });
    } catch (e) {
      console.warn("Failed to sync mark-all-read with backend:", e);
    }
  };

  const markAsRead = async (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      await fetch(`${API_BASE_URL}/api/v1/notifications/${id}/read`, {
        method: "PATCH",
        headers,
      });
    } catch (e) {
      console.warn(`Failed to sync mark-read for ${id}:`, e);
    }
  };

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
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white/80 backdrop-blur-md px-4 py-3 rounded-2xl shadow-xs print:hidden mb-6">
        {/* Left side: branding & nav links */}
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

        {/* Right side: Notifications, AI Assistant & Institute Pill */}
        <div className="flex items-center gap-2">
          {/* Notification Bell Dropdown */}
          <div className="relative" ref={notificationRef}>
            <button
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              className={`relative flex h-9 w-9 sm:h-9 sm:w-9 min-h-[38px] min-w-[38px] items-center justify-center rounded-xl border transition-all ${
                isNotificationsOpen
                  ? "bg-indigo-50 border-indigo-300 text-indigo-600 shadow-xs"
                  : "bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 shadow-2xs"
              }`}
              aria-label="Toggle notifications dropdown"
              aria-expanded={isNotificationsOpen}
            >
              <Bell className="h-4 w-4" />
              {/* Dynamic Red Notification Badge over Bell icon: Hidden if count is 0 */}
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white ring-2 ring-white animate-pulse">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {/* Mobile-Responsive Dropdown Menu */}
            {isNotificationsOpen && (
              <div 
                className="fixed inset-x-3 top-16 sm:absolute sm:inset-auto sm:right-0 sm:mt-2 sm:w-96 max-w-[calc(100vw-1.5rem)] rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/50 z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
                role="menu"
                aria-orientation="vertical"
              >
                {/* Dropdown Header */}
                <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Notifications
                    </h4>
                    {unreadCount > 0 && (
                      <span className="rounded-full bg-rose-100 text-rose-700 px-2 py-0.5 text-[10px] font-bold">
                        {unreadCount} unread
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer"
                    >
                      <CheckCheck className="h-3.5 w-3.5" />
                      <span>Mark all as read</span>
                    </button>
                  )}
                </div>

                {/* Notification Items List */}
                <div className="max-h-80 sm:max-h-96 overflow-y-auto divide-y divide-slate-100">
                  {notifications.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-400">
                      No notifications at this time
                    </div>
                  ) : (
                    notifications.map((item) => {
                      let IconComponent = Bell;
                      let iconColor = "bg-slate-100 text-slate-600";

                      if (item.type === "exam") {
                        IconComponent = Calendar;
                        iconColor = "bg-amber-100 text-amber-700";
                      } else if (item.type === "weak_topic") {
                        IconComponent = AlertTriangle;
                        iconColor = "bg-rose-100 text-rose-700";
                      } else if (item.type === "adaptive") {
                        IconComponent = Sparkles;
                        iconColor = "bg-indigo-100 text-indigo-700";
                      } else if (item.type === "course") {
                        IconComponent = BookOpen;
                        iconColor = "bg-emerald-100 text-emerald-700";
                      }

                      return (
                        <div
                          key={item.id}
                          onClick={() => markAsRead(item.id)}
                          className={`p-3.5 text-left transition-colors cursor-pointer hover:bg-slate-50 flex items-start gap-3 ${
                            !item.is_read ? "bg-indigo-50/40" : "bg-white"
                          }`}
                        >
                          <div
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${iconColor}`}
                          >
                            <IconComponent className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <p className={`text-xs truncate ${!item.is_read ? "font-bold text-slate-900" : "font-medium text-slate-700"}`}>
                                {item.title}
                              </p>
                              <span className="text-[10px] text-slate-400 shrink-0">
                                {item.time}
                              </span>
                            </div>
                            <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                              {item.description}
                            </p>
                          </div>
                          {!item.is_read && (
                            <span className="mt-1 h-2 w-2 rounded-full bg-rose-500 shrink-0 ring-2 ring-rose-100" />
                          )}
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Dropdown Footer */}
                <div className="border-t border-slate-100 bg-slate-50/50 px-4 py-2 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="font-medium">Live Telemetry Alerts</span>
                  <span>{notifications.length} total</span>
                </div>
              </div>
            )}
          </div>

          {/* AI Assistant Drawer Trigger Button */}
          <button
            onClick={() => setIsAiDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-linear-to-r from-indigo-600 to-violet-600 px-3 py-2 text-xs font-semibold text-white hover:from-indigo-700 hover:to-violet-700 transition-all shadow-xs shadow-indigo-200 active:scale-98 min-h-[38px]"
            aria-label="Open AI Assistant Drawer"
            title="Open AI Assistant"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">AI Assistant</span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </button>

          {/* SKIT Badge */}
          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              SKIT CSE • 2026-27
            </span>
          </div>
        </div>
      </div>

      {/* AI Assistant Sliding Drawer */}
      <AiAssistantDrawer
        isOpen={isAiDrawerOpen}
        onClose={() => setIsAiDrawerOpen(false)}
      />
    </>
  );
}
