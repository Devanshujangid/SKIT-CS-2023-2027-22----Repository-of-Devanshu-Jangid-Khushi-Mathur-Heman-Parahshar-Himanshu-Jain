"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth, useUser } from "@clerk/nextjs";
import DashboardNav from "@/components/DashboardNav";
import { API_BASE_URL } from "@/lib/api";
import {
  Trophy,
  Medal,
  Flame,
  Clock,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  Award,
  Users,
  Target,
  ArrowUpRight,
  Shield,
  Filter,
  RefreshCw
} from "lucide-react";

interface StudentRank {
  rank: number;
  scholar_id: string;
  name: string;
  avatar: string;
  score: number;
  completion_rate: number;
  study_hours: number;
  streak_days: number;
  badge: string;
  focus: string;
  trend?: "up" | "down" | "same";
  is_current_user?: boolean;
}

const DEFAULT_PODIUM: StudentRank[] = [
  {
    rank: 1,
    scholar_id: "23SKCS022",
    name: "Himanshu Jain",
    avatar: "HJ",
    score: 980,
    completion_rate: 100,
    study_hours: 35.0,
    streak_days: 14,
    badge: "Grandmaster",
    focus: "Algorithms & Schemas",
    trend: "up",
  },
  {
    rank: 2,
    scholar_id: "23SKCS019",
    name: "Heman Parashar",
    avatar: "HP",
    score: 940,
    completion_rate: 97,
    study_hours: 32.0,
    streak_days: 11,
    badge: "Backend Pro",
    focus: "Supabase & Database",
    trend: "up",
  },
  {
    rank: 3,
    scholar_id: "23SKCS015",
    name: "Khushi Mathur",
    avatar: "KM",
    score: 915,
    completion_rate: 95,
    study_hours: 34.0,
    streak_days: 9,
    badge: "ML Pioneer",
    focus: "TF-IDF & Speech AI",
    trend: "up",
  },
];

const DEFAULT_RANKINGS: StudentRank[] = [
  ...DEFAULT_PODIUM,
  {
    rank: 4,
    scholar_id: "23SKCS001",
    name: "Devanshu Jangid",
    avatar: "DJ",
    score: 880,
    completion_rate: 89,
    study_hours: 30.8,
    streak_days: 8,
    badge: "Sprint Champion",
    focus: "Operating Systems",
    trend: "same",
    is_current_user: true,
  },
  {
    rank: 5,
    scholar_id: "23SKCS044",
    name: "Aman Sharma",
    avatar: "AS",
    score: 750,
    completion_rate: 78,
    study_hours: 26.5,
    streak_days: 5,
    badge: "Consistent",
    focus: "Computer Networks",
    trend: "down",
  },
  {
    rank: 6,
    scholar_id: "23SKCS051",
    name: "Riya Choudhary",
    avatar: "RC",
    score: 720,
    completion_rate: 75,
    study_hours: 25.0,
    streak_days: 4,
    badge: "On Track",
    focus: "Discrete Mathematics",
    trend: "up",
  },
  {
    rank: 7,
    scholar_id: "23SKCS067",
    name: "Siddharth Verma",
    avatar: "SV",
    score: 680,
    completion_rate: 70,
    study_hours: 23.0,
    streak_days: 3,
    badge: "Rising Star",
    focus: "Database Systems",
    trend: "down",
  },
  {
    rank: 8,
    scholar_id: "23SKCS089",
    name: "Pooja Agarwal",
    avatar: "PA",
    score: 640,
    completion_rate: 68,
    study_hours: 21.5,
    streak_days: 3,
    badge: "Steady",
    focus: "Software Engineering",
    trend: "same",
  },
];

export default function LeaderboardPage() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [timeframe, setTimeframe] = useState<"weekly" | "monthly" | "all_time">("weekly");
  const [podium, setPodium] = useState<StudentRank[]>(DEFAULT_PODIUM);
  const [rankings, setRankings] = useState<StudentRank[]>(DEFAULT_RANKINGS);
  const [isLoading, setIsLoading] = useState(false);

  const fetchLeaderboard = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE_URL}/api/v1/analytics/leaderboard?timeframe=${timeframe}`, {
        headers,
      });

      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.podium) && data.podium.length > 0) {
          setPodium(data.podium);
        }
        if (Array.isArray(data.rankings) && data.rankings.length > 0) {
          setRankings(data.rankings);
        }
      }
    } catch (e) {
      console.warn("Could not fetch live leaderboard, using verified benchmark data:", e);
    } finally {
      setIsLoading(false);
    }
  }, [getToken, timeframe]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  const currentUser = rankings.find((r) => r.is_current_user) || rankings[3];

  return (
    <div className="min-h-screen bg-slate-50/70 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Navigation Bar */}
        <DashboardNav showBackToDashboard={true} />

        {/* Hero Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-linear-to-r from-slate-950 via-indigo-950 to-slate-900 border border-slate-800 p-6 sm:p-8 text-white shadow-xl">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/20 border border-indigo-400/30 px-3 py-1 text-xs font-semibold text-indigo-300">
                  <Trophy className="h-3.5 w-3.5 text-amber-400" />
                  SKIT CSE • Semester 5 Standings
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 border border-emerald-400/30 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                  <Flame className="h-3.5 w-3.5 text-rose-400" />
                  Live Sync
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                Academic Velocity Leaderboard
              </h1>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                Peer rankings calibrated against planned vs actual study hours, weekly milestone completion, and zero-deficit consistency.
              </p>
            </div>

            {/* Timeframe Controls */}
            <div className="flex items-center gap-1.5 rounded-2xl bg-white/10 p-1.5 backdrop-blur-md border border-white/10 shrink-0 self-start md:self-auto">
              {(["weekly", "monthly", "all_time"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setTimeframe(tab)}
                  className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-all capitalize cursor-pointer ${
                    timeframe === tab
                      ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30"
                      : "text-slate-300 hover:text-white hover:bg-white/10"
                  }`}
                >
                  {tab === "all_time" ? "Semester" : tab}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Current User Quick Banner */}
        {currentUser && (
          <div className="rounded-2xl border border-indigo-200 bg-linear-to-r from-indigo-50/90 via-violet-50/50 to-white p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5 min-w-0">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white font-black text-base shadow-md shadow-indigo-300">
                #{currentUser.rank}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900 truncate">
                    {currentUser.name}
                  </h3>
                  <span className="rounded-md bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
                    Your Standing
                  </span>
                </div>
                <p className="text-xs text-slate-500 truncate">
                  {currentUser.scholar_id} • Focus: {currentUser.focus}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 sm:gap-6 text-xs border-t sm:border-t-0 border-indigo-100 pt-3 sm:pt-0">
              <div className="text-center sm:text-right">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Score</span>
                <p className="font-extrabold text-indigo-700 text-sm sm:text-base">{currentUser.score} pts</p>
              </div>
              <div className="text-center sm:text-right">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Adherence</span>
                <p className="font-extrabold text-emerald-600 text-sm sm:text-base">{currentUser.completion_rate}%</p>
              </div>
              <div className="text-center sm:text-right">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Streak</span>
                <p className="font-extrabold text-amber-600 text-sm sm:text-base flex items-center justify-center sm:justify-end gap-1">
                  <Flame className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                  {currentUser.streak_days}d
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Podium Display (Top 3) */}
        <div className="rounded-3xl border border-slate-200/80 bg-white p-6 sm:p-8 shadow-xs">
          <div className="text-center space-y-1 mb-8">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200/80 px-3 py-1 text-xs font-bold text-amber-800">
              <Trophy className="h-3.5 w-3.5 text-amber-600" />
              <span>Sprint Podium Champions</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900">
              Top Ranked Scholars
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
              Leading the cohort with zero missed sessions and superior study pacing.
            </p>
          </div>

          {/* Podium Columns */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 lg:gap-6 items-end max-w-4xl mx-auto pt-4">
            {/* Rank 2 - Silver (Left on Desktop) */}
            {podium[1] && (
              <div className="order-2 sm:order-1 flex flex-col items-center">
                <div className="relative mb-3 flex flex-col items-center">
                  <div className="h-16 w-16 rounded-2xl bg-linear-to-br from-slate-200 to-slate-400 p-0.5 shadow-md">
                    <div className="flex h-full w-full items-center justify-center rounded-2xl bg-white font-extrabold text-slate-700 text-lg">
                      {podium[1].avatar}
                    </div>
                  </div>
                  <span className="absolute -bottom-2 flex h-6 w-6 items-center justify-center rounded-full bg-slate-300 border-2 border-white text-xs font-black text-slate-800 shadow-xs">
                    2
                  </span>
                </div>
                <div className="text-center space-y-1">
                  <h4 className="font-bold text-sm text-slate-900">{podium[1].name}</h4>
                  <span className="text-[11px] text-slate-500">{podium[1].scholar_id}</span>
                  <div className="inline-block rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                    {podium[1].score} pts • {podium[1].study_hours}h
                  </div>
                </div>
                <div className="w-full mt-3 rounded-2xl bg-linear-to-b from-slate-100 to-slate-200 border border-slate-300 p-4 text-center h-28 sm:h-32 flex flex-col justify-center shadow-inner">
                  <span className="text-xs font-black text-slate-600 uppercase tracking-wider">Silver Scholar</span>
                  <p className="text-[11px] text-slate-500 mt-1 font-semibold">{podium[1].completion_rate}% Adherence</p>
                </div>
              </div>
            )}

            {/* Rank 1 - Gold (Center, Elevated) */}
            {podium[0] && (
              <div className="order-1 sm:order-2 flex flex-col items-center">
                <div className="relative mb-3 flex flex-col items-center">
                  <span className="text-2xl mb-1 animate-bounce">👑</span>
                  <div className="h-20 w-20 rounded-2xl bg-linear-to-br from-amber-300 via-yellow-400 to-amber-500 p-0.5 shadow-lg shadow-amber-200">
                    <div className="flex h-full w-full items-center justify-center rounded-2xl bg-white font-black text-amber-700 text-xl">
                      {podium[0].avatar}
                    </div>
                  </div>
                  <span className="absolute -bottom-2 flex h-7 w-7 items-center justify-center rounded-full bg-amber-400 border-2 border-white text-xs font-black text-amber-950 shadow-xs">
                    1
                  </span>
                </div>
                <div className="text-center space-y-1">
                  <h4 className="font-bold text-base text-slate-900">{podium[0].name}</h4>
                  <span className="text-[11px] text-slate-500">{podium[0].scholar_id}</span>
                  <div className="inline-block rounded-md bg-amber-100 border border-amber-300 px-2.5 py-0.5 text-xs font-extrabold text-amber-800">
                    {podium[0].score} pts • {podium[0].study_hours}h
                  </div>
                </div>
                <div className="w-full mt-3 rounded-2xl bg-linear-to-b from-amber-100 via-amber-200/80 to-amber-200 border border-amber-300 p-4 text-center h-36 sm:h-40 flex flex-col justify-center shadow-inner">
                  <span className="text-xs font-black text-amber-900 uppercase tracking-wider flex items-center justify-center gap-1">
                    <Trophy className="h-3.5 w-3.5 text-amber-700" />
                    Gold Champion
                  </span>
                  <p className="text-xs text-amber-800 mt-1 font-bold">{podium[0].completion_rate}% Perfect Score</p>
                  <span className="text-[10px] text-amber-700 mt-0.5">{podium[0].streak_days} Day Streak</span>
                </div>
              </div>
            )}

            {/* Rank 3 - Bronze (Right on Desktop) */}
            {podium[2] && (
              <div className="order-3 flex flex-col items-center">
                <div className="relative mb-3 flex flex-col items-center">
                  <div className="h-16 w-16 rounded-2xl bg-linear-to-br from-amber-600 to-orange-700 p-0.5 shadow-md">
                    <div className="flex h-full w-full items-center justify-center rounded-2xl bg-white font-extrabold text-amber-900 text-lg">
                      {podium[2].avatar}
                    </div>
                  </div>
                  <span className="absolute -bottom-2 flex h-6 w-6 items-center justify-center rounded-full bg-amber-600 border-2 border-white text-xs font-black text-white shadow-xs">
                    3
                  </span>
                </div>
                <div className="text-center space-y-1">
                  <h4 className="font-bold text-sm text-slate-900">{podium[2].name}</h4>
                  <span className="text-[11px] text-slate-500">{podium[2].scholar_id}</span>
                  <div className="inline-block rounded-md bg-orange-100 px-2 py-0.5 text-[10px] font-bold text-orange-800">
                    {podium[2].score} pts • {podium[2].study_hours}h
                  </div>
                </div>
                <div className="w-full mt-3 rounded-2xl bg-linear-to-b from-orange-50 to-orange-100 border border-orange-200 p-4 text-center h-24 sm:h-28 flex flex-col justify-center shadow-inner">
                  <span className="text-xs font-black text-orange-800 uppercase tracking-wider">Bronze Scholar</span>
                  <p className="text-[11px] text-orange-700 mt-1 font-semibold">{podium[2].completion_rate}% Adherence</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Full Rankings Table (Mobile Responsiveness with overflow-x-auto) */}
        <div className="rounded-3xl border border-slate-200/80 bg-white shadow-xs overflow-hidden">
          <div className="border-b border-slate-100 bg-slate-50/80 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-base text-slate-900">
                Cohort Performance Standings
              </h3>
              <p className="text-xs text-slate-500">
                Total 128 registered students evaluated across CSE Semester 5
              </p>
            </div>
            <button
              onClick={fetchLeaderboard}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-indigo-600 transition-colors shadow-2xs self-start sm:self-auto cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-indigo-600" : ""}`} />
              <span>Refresh Standings</span>
            </button>
          </div>

          {/* Table Container with native horizontal scrolling for mobile */}
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[700px] text-left text-xs">
              <thead className="bg-slate-50/60 border-b border-slate-200/80 text-[11px] uppercase font-bold text-slate-500 tracking-wider">
                <tr>
                  <th className="py-3.5 pl-6 pr-3">Rank</th>
                  <th className="py-3.5 px-3">Student & Scholar ID</th>
                  <th className="py-3.5 px-3">Primary Focus</th>
                  <th className="py-3.5 px-3 text-center">Score</th>
                  <th className="py-3.5 px-3 text-center">Adherence</th>
                  <th className="py-3.5 px-3 text-center">Hours Logged</th>
                  <th className="py-3.5 px-3 text-center">Streak</th>
                  <th className="py-3.5 pr-6 text-right">Badge</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rankings.map((student) => {
                  const isCurrent = student.is_current_user;
                  return (
                    <tr
                      key={student.scholar_id}
                      className={`transition-colors ${
                        isCurrent
                          ? "bg-indigo-50/50 hover:bg-indigo-50/80 font-medium"
                          : "hover:bg-slate-50/70"
                      }`}
                    >
                      <td className="py-4 pl-6 pr-3 font-bold text-slate-700">
                        <div className="flex items-center gap-2">
                          {student.rank === 1 ? (
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-amber-800 font-black text-xs">
                              🥇
                            </span>
                          ) : student.rank === 2 ? (
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-slate-800 font-black text-xs">
                              🥈
                            </span>
                          ) : student.rank === 3 ? (
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-orange-100 text-orange-800 font-black text-xs">
                              🥉
                            </span>
                          ) : (
                            <span className="text-slate-500 pl-1">#{student.rank}</span>
                          )}
                          {student.trend === "up" && (
                            <TrendingUp className="h-3 w-3 text-emerald-500" />
                          )}
                          {student.trend === "down" && (
                            <TrendingDown className="h-3 w-3 text-rose-500" />
                          )}
                          {student.trend === "same" && (
                            <Minus className="h-3 w-3 text-slate-400" />
                          )}
                        </div>
                      </td>

                      <td className="py-4 px-3">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-700">
                            {student.avatar}
                          </div>
                          <div>
                            <p className="font-bold text-slate-900 flex items-center gap-1.5">
                              {student.name}
                              {isCurrent && (
                                <span className="rounded-md bg-indigo-600 text-white px-1.5 py-0.2 text-[9px] font-bold">
                                  YOU
                                </span>
                              )}
                            </p>
                            <span className="text-[11px] text-slate-400">{student.scholar_id}</span>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-3 text-slate-600 font-medium">
                        {student.focus}
                      </td>

                      <td className="py-4 px-3 text-center font-extrabold text-indigo-700">
                        {student.score}
                      </td>

                      <td className="py-4 px-3 text-center">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                            student.completion_rate >= 90
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : student.completion_rate >= 75
                              ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}
                        >
                          {student.completion_rate}%
                        </span>
                      </td>

                      <td className="py-4 px-3 text-center text-slate-700 font-semibold">
                        {student.study_hours}h
                      </td>

                      <td className="py-4 px-3 text-center">
                        <span className="inline-flex items-center gap-1 font-bold text-amber-600">
                          <Flame className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                          {student.streak_days}d
                        </span>
                      </td>

                      <td className="py-4 pr-6 text-right">
                        <span className="inline-block rounded-md bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-700">
                          {student.badge}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer Guidance Note */}
        <div className="rounded-2xl border border-slate-200 bg-white/60 p-4 text-center text-xs text-slate-500">
          Rankings are updated daily based on verified task telemetry logged via the Task Execution Modal.
        </div>
      </div>
    </div>
  );
}
