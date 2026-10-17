"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Clock,
  BookOpen,
  ArrowRight,
  CheckCircle2,
  X,
} from "lucide-react";

export interface MissedTaskDetail {
  id: string;
  subject: string;
  topic: string;
  day?: string;
  missed_minutes: number;
  reason?: string;
}

interface AdaptiveScheduleBannerProps {
  missedCount: number;
  missedMinutes: number;
  affectedSubjects: string[];
  missedTasks: MissedTaskDetail[];
  onRebalance: () => Promise<void>;
  isRebalancing: boolean;
  onDismiss?: () => void;
}

export default function AdaptiveScheduleBanner({
  missedCount,
  missedMinutes,
  affectedSubjects,
  missedTasks,
  onRebalance,
  isRebalancing,
  onDismiss,
}: AdaptiveScheduleBannerProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);

  if (isDismissed || missedCount <= 0) return null;

  return (
    <div
      role="alert"
      className="relative overflow-hidden rounded-2xl border border-amber-300/80 bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/5 p-5 shadow-sm transition-all animate-in fade-in slide-in-from-top-2 duration-300"
    >
      {/* Decorative gradient blur */}
      <div className="absolute -top-12 -right-12 h-36 w-36 rounded-full bg-amber-400/10 blur-2xl pointer-events-none" />

      <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {/* Left Side: Icon & Details */}
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 text-white shadow-md shadow-amber-500/20">
            <AlertTriangle className="h-5 w-5 animate-pulse" />
          </div>

          <div className="space-y-1 min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/15 text-amber-900 border border-amber-400/30">
                <Sparkles className="h-3 w-3 text-amber-600" />
                Adaptive Schedule Adjustment Needed
              </span>
              <span className="text-xs font-medium text-slate-500">
                {missedCount} missed {missedCount === 1 ? "task" : "tasks"} detected
              </span>
            </div>

            <h4 className="text-sm sm:text-base font-bold text-slate-900">
              Catch up required: {missedMinutes} minutes behind schedule
            </h4>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              You missed planned study sessions in{" "}
              <strong className="text-slate-900">{affectedSubjects.join(", ")}</strong> from
              previous days. Your learning velocity has fallen behind target.
            </p>

            {/* Chips for affected subjects */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {missedTasks.slice(0, 3).map((item) => (
                <span
                  key={item.id}
                  className="inline-flex items-center gap-1 rounded-md bg-white/80 px-2 py-0.5 text-xs font-medium text-slate-700 border border-amber-200/60 shadow-xs"
                >
                  <BookOpen className="h-3 w-3 text-amber-600" />
                  <span className="font-semibold text-slate-900">{item.subject}:</span> {item.topic}
                  <span className="text-rose-600 font-bold ml-0.5">(-{item.missed_minutes}m)</span>
                </span>
              ))}
              {missedTasks.length > 3 && (
                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs font-semibold text-amber-800 hover:underline cursor-pointer"
                >
                  +{missedTasks.length - 3} more
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right Side: CTA Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0 self-start md:self-center">
          <button
            type="button"
            onClick={onRebalance}
            disabled={isRebalancing}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-2.5 text-xs sm:text-sm font-bold text-white shadow-md shadow-amber-600/25 hover:from-amber-700 hover:to-orange-700 active:scale-95 transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isRebalancing ? "animate-spin" : ""}`} />
            <span>{isRebalancing ? "Rebalancing Schedule..." : "Adjust & Rebalance Schedule"}</span>
          </button>

          {onDismiss && (
            <button
              type="button"
              onClick={() => {
                setIsDismissed(true);
                onDismiss();
              }}
              className="rounded-xl p-2 text-slate-400 hover:bg-amber-100/50 hover:text-slate-600 transition-colors cursor-pointer"
              aria-label="Dismiss alert"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Expandable Breakdown Drawer */}
      {isExpanded && missedTasks.length > 3 && (
        <div className="mt-4 pt-3 border-t border-amber-200/60 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {missedTasks.map((t) => (
            <div
              key={t.id}
              className="rounded-lg bg-white/70 p-2.5 border border-amber-200/50 text-xs flex items-center justify-between"
            >
              <div>
                <span className="font-bold text-slate-900">{t.subject}</span>: {t.topic}
                {t.day && <span className="text-slate-400 ml-1">({t.day})</span>}
              </div>
              <span className="font-bold text-rose-600 shrink-0 ml-2">-{t.missed_minutes}m</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
