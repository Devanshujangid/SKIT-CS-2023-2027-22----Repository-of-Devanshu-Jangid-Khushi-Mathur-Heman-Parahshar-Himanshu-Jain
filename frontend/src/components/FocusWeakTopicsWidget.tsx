"use client";

import React from "react";
import {
  AlertCircle,
  Tag,
  BookOpen,
  ArrowRight,
  TrendingDown,
  CheckCircle2,
  Clock,
  Sparkles,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

export interface WeakTopicItem {
  id: string;
  subject: string;
  topic: string;
  status: "Needs Revision" | "On Track";
  severity: "high" | "medium" | "low";
  explainability_tags: string[];
  missed_minutes: number;
  planned_minutes: number;
  actual_minutes: number;
  recommended_query: string;
}

interface FocusWeakTopicsWidgetProps {
  weakTopics: WeakTopicItem[];
  onSelectTopicForRecommendations?: (query: string) => void;
  isLoading?: boolean;
}

export default function FocusWeakTopicsWidget({
  weakTopics,
  onSelectTopicForRecommendations,
  isLoading = false,
}: FocusWeakTopicsWidgetProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-4 animate-pulse">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="space-y-2">
            <div className="h-5 w-48 bg-slate-200 rounded" />
            <div className="h-3.5 w-72 bg-slate-200 rounded" />
          </div>
          <div className="h-8 w-24 bg-slate-200 rounded-full" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-32 bg-slate-100 rounded-xl" />
          <div className="h-32 bg-slate-100 rounded-xl" />
        </div>
      </div>
    );
  }

  const needsRevisionCount = weakTopics.filter((t) => t.status === "Needs Revision").length;

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-50 text-rose-600">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              Focus & Weak Topics
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic diagnostics based on missed tasks, study deficits, and topic mastery
          </p>
        </div>

        {/* Status Pill */}
        {needsRevisionCount > 0 ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700 border border-rose-200 self-start sm:self-auto">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
            {needsRevisionCount} {needsRevisionCount === 1 ? "Subject" : "Subjects"} Need Revision
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200 self-start sm:self-auto">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            All Topics On Track
          </span>
        )}
      </div>

      {/* Content Grid */}
      {weakTopics.length === 0 ? (
        <div className="rounded-xl bg-slate-50 p-6 text-center border border-slate-100 space-y-2">
          <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto" />
          <h4 className="text-sm font-bold text-slate-800">No Weak Topics Identified</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            You are fully caught up on all scheduled tasks. When tasks are missed or study deficits occur, deterministic diagnostics will highlight areas needing review here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {weakTopics.map((item) => {
            const isWeak = item.status === "Needs Revision";
            const percentCompletion = item.planned_minutes > 0
              ? Math.min(100, Math.round((item.actual_minutes / item.planned_minutes) * 100))
              : 0;

            return (
              <div
                key={item.id}
                className={`flex flex-col justify-between rounded-xl p-4.5 border transition-all ${
                  isWeak
                    ? "bg-gradient-to-br from-rose-50/40 via-white to-amber-50/30 border-rose-200 hover:border-rose-300 shadow-xs"
                    : "bg-white border-slate-200"
                }`}
              >
                <div className="space-y-3">
                  {/* Top Bar: Subject & Status Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700">
                      {item.subject}
                    </span>

                    {isWeak ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-200">
                        <AlertCircle className="h-3 w-3" />
                        Needs Revision
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                        <CheckCircle2 className="h-3 w-3" />
                        On Track
                      </span>
                    )}
                  </div>

                  {/* Topic Title */}
                  <div>
                    <h4 className="text-sm sm:text-base font-bold text-slate-900">
                      {item.topic}
                    </h4>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <span>Studied: <strong>{item.actual_minutes}m</strong> of {item.planned_minutes}m</span>
                      <span>•</span>
                      <span className={isWeak ? "text-rose-600 font-semibold" : "text-slate-600"}>
                        {percentCompletion}% completed
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        percentCompletion < 50
                          ? "bg-rose-500"
                          : percentCompletion < 80
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${percentCompletion}%` }}
                    />
                  </div>

                  {/* Deterministic Explainability Tags */}
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Deterministic Explainability
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {item.explainability_tags.map((tag, tagIdx) => (
                        <span
                          key={tagIdx}
                          className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 shadow-2xs"
                        >
                          <Tag className="h-2.5 w-2.5 text-indigo-500" />
                          <span>{tag}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bottom Action CTA */}
                {onSelectTopicForRecommendations && (
                  <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[11px] text-slate-500">
                      Targeted Coursera resources ready
                    </span>
                    <button
                      type="button"
                      onClick={() => onSelectTopicForRecommendations(item.recommended_query)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700 hover:underline cursor-pointer"
                    >
                      <span>Find Targeted Resources</span>
                      <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
