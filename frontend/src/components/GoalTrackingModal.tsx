"use client";

import React from "react";
import Link from "next/link";
import {
  Trophy,
  Award,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Sparkles,
  ArrowRight,
  RefreshCw,
  X,
  Target,
  Clock,
  ShieldAlert,
  Flame,
} from "lucide-react";

export interface GoalMetrics {
  adherenceRate: number; // e.g. 88%
  completionRate: number; // e.g. 90%
  completedHours: number; // e.g. 30.8
  scheduledHours: number; // e.g. 34.5
  completedTasksCount: number;
  totalTasksCount: number;
  missedTasksCount: number;
  targetGoal?: string;
  isDeficit?: boolean;
}

interface GoalTrackingModalProps {
  isOpen: boolean;
  onClose: () => void;
  metrics: GoalMetrics;
  onTriggerRebalance?: () => void;
}

export default function GoalTrackingModal({
  isOpen,
  onClose,
  metrics,
  onTriggerRebalance,
}: GoalTrackingModalProps) {
  if (!isOpen) return null;

  const isSuccess = metrics.adherenceRate >= 80 && metrics.missedTasksCount === 0;
  const isAtRisk = metrics.adherenceRate < 65 || metrics.missedTasksCount > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="goal-modal-title"
    >
      <div
        className={`relative w-full max-w-lg rounded-3xl border bg-white shadow-2xl overflow-hidden transition-all duration-300 ${
          isSuccess
            ? "border-emerald-200 shadow-emerald-500/10"
            : isAtRisk
            ? "border-amber-300 shadow-amber-500/10"
            : "border-indigo-200 shadow-indigo-500/10"
        }`}
      >
        {/* Top Header Background Glow */}
        <div
          className={`h-2.5 w-full ${
            isSuccess
              ? "bg-linear-to-r from-emerald-500 via-teal-400 to-emerald-600"
              : isAtRisk
              ? "bg-linear-to-r from-amber-500 via-orange-400 to-rose-500"
              : "bg-linear-to-r from-indigo-500 via-blue-400 to-cyan-500"
          }`}
        />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 rounded-full p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer z-10"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="p-6 sm:p-8 space-y-6">
          {/* Status Badge & Icon */}
          <div className="flex flex-col items-center text-center space-y-3">
            <div
              className={`flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl shadow-inner ${
                isSuccess
                  ? "bg-emerald-100 text-emerald-600 border border-emerald-200"
                  : isAtRisk
                  ? "bg-amber-100 text-amber-600 border border-amber-200"
                  : "bg-indigo-100 text-indigo-600 border border-indigo-200"
              }`}
            >
              {isSuccess ? (
                <Trophy className="h-8 w-8 sm:h-10 sm:w-10 animate-bounce" />
              ) : isAtRisk ? (
                <AlertTriangle className="h-8 w-8 sm:h-10 sm:w-10 animate-pulse text-amber-600" />
              ) : (
                <Target className="h-8 w-8 sm:h-10 sm:w-10 text-indigo-600" />
              )}
            </div>

            <div>
              <div
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                  isSuccess
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : isAtRisk
                    ? "bg-amber-50 text-amber-800 border border-amber-200"
                    : "bg-indigo-50 text-indigo-800 border border-indigo-200"
                }`}
              >
                {isSuccess ? (
                  <>
                    <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Goal Milestone Achieved!</span>
                  </>
                ) : isAtRisk ? (
                  <>
                    <ShieldAlert className="h-3.5 w-3.5 text-amber-600" />
                    <span>Goal Trajectory Warning</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-indigo-600" />
                    <span>Goal Progress On Track</span>
                  </>
                )}
              </div>

              <h2
                id="goal-modal-title"
                className="mt-2 text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight"
              >
                {isSuccess
                  ? "Weekly Study Target Completed!"
                  : isAtRisk
                  ? "Study Deficit Detected: Action Required"
                  : "Consistent Study Pace Maintained"}
              </h2>

              <p className="mt-1 text-xs sm:text-sm text-slate-600 max-w-sm mx-auto leading-relaxed">
                {isSuccess
                  ? `Incredible dedication! You have sustained an exceptional ${metrics.adherenceRate}% adherence rate across your 7-day academic plan.`
                  : isAtRisk
                  ? `Telemetry flags indicate ${metrics.missedTasksCount} missed or shortened session(s). Your current adherence is ${metrics.adherenceRate}%, dipping below the 80% semester threshold.`
                  : `You are on pace to fulfill your active semester study targets with an adherence rate of ${metrics.adherenceRate}%.`}
              </p>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-3 gap-2.5 sm:gap-3 rounded-2xl bg-slate-50 border border-slate-200/80 p-3 sm:p-4 text-center">
            <div className="p-2 sm:p-3 rounded-xl bg-white border border-slate-100 shadow-2xs">
              <span className="block text-[10px] sm:text-xs font-bold text-slate-500 uppercase tracking-wider">
                Adherence
              </span>
              <div
                className={`mt-1 text-lg sm:text-2xl font-black ${
                  metrics.adherenceRate >= 80
                    ? "text-emerald-600"
                    : metrics.adherenceRate < 65
                    ? "text-rose-600"
                    : "text-amber-600"
                }`}
              >
                {metrics.adherenceRate}%
              </div>
              <span className="text-[10px] text-slate-400">Target ≥ 80%</span>
            </div>

            <div className="p-2 sm:p-3 rounded-xl bg-white border border-slate-100 shadow-2xs">
              <span className="block text-[10px] sm:text-xs font-bold text-slate-500 uppercase tracking-wider">
                Logged Hours
              </span>
              <div className="mt-1 text-lg sm:text-2xl font-black text-slate-900">
                {metrics.completedHours}h
              </div>
              <span className="text-[10px] text-slate-400">of {metrics.scheduledHours}h</span>
            </div>

            <div className="p-2 sm:p-3 rounded-xl bg-white border border-slate-100 shadow-2xs">
              <span className="block text-[10px] sm:text-xs font-bold text-slate-500 uppercase tracking-wider">
                Completed
              </span>
              <div className="mt-1 text-lg sm:text-2xl font-black text-indigo-600">
                {metrics.completedTasksCount}/{metrics.totalTasksCount}
              </div>
              <span className="text-[10px] text-slate-400">Tasks</span>
            </div>
          </div>

          {/* Actionable Strategy Box */}
          {isAtRisk ? (
            <div className="rounded-2xl bg-amber-50/80 border border-amber-200 p-4 space-y-2">
              <div className="flex items-center gap-2 text-amber-900 font-bold text-xs">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                <span>Automated Diagnostic Action</span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                Deterministic catch-up rule can rebalance your remaining days. It shifts missed sessions forward while strictly enforcing your daily study ceiling.
              </p>
            </div>
          ) : (
            <div className="rounded-2xl bg-emerald-50/80 border border-emerald-200 p-4 space-y-2">
              <div className="flex items-center gap-2 text-emerald-900 font-bold text-xs">
                <Flame className="h-4 w-4 text-emerald-600 shrink-0" />
                <span>Streak & Leaderboard Surge</span>
              </div>
              <p className="text-xs text-emerald-800 leading-relaxed">
                Your discipline puts you in the top tier of your engineering cohort. Check the new Leaderboard to see your updated rank!
              </p>
            </div>
          )}

          {/* Modal Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            {isAtRisk && onTriggerRebalance ? (
              <button
                onClick={() => {
                  onTriggerRebalance();
                  onClose();
                }}
                className="w-full sm:flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs sm:text-sm py-3 px-4 shadow-md transition-colors cursor-pointer"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Auto-Rebalance Schedule</span>
              </button>
            ) : isSuccess ? (
              <Link
                href="/dashboard/leaderboard"
                onClick={onClose}
                className="w-full sm:flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs sm:text-sm py-3 px-4 shadow-md transition-colors cursor-pointer"
              >
                <Trophy className="h-4 w-4" />
                <span>View Cohort Leaderboard</span>
              </Link>
            ) : null}

            <button
              onClick={onClose}
              className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm py-3 px-5 transition-colors cursor-pointer"
            >
              Continue Studying
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
