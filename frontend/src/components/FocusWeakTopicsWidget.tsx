"use client";

import React from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Sparkles,
  Tag,
  Target,
} from "lucide-react";

export interface WeakTopicItem {
  id: string;
  subject: string;
  topic: string;
  status: "Needs Revision" | "On Track" | string;
  severity: "high" | "medium" | "low" | string;
  explainability_tags: string[];
  missed_minutes?: number;
  planned_minutes?: number;
  actual_minutes?: number;
  recommended_query: string;
}

export interface FocusWeakTopicsWidgetProps {
  weakTopics: WeakTopicItem[];
  isLoading?: boolean;
  onSelectTopicForRecommendations: (recommended_query: string) => void;
}

export default function FocusWeakTopicsWidget({
  weakTopics,
  isLoading = false,
  onSelectTopicForRecommendations,
}: FocusWeakTopicsWidgetProps) {
  // Skeleton Loading State matching design system
  if (isLoading) {
    return (
      <section className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-5 animate-pulse">
        {/* Header Skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-slate-200" />
              <div className="h-6 w-48 rounded bg-slate-200" />
            </div>
            <div className="h-3.5 w-72 rounded bg-slate-100" />
          </div>
          <div className="h-7 w-32 rounded-full bg-slate-200 self-start sm:self-auto" />
        </div>

        {/* Cards Grid Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((idx) => (
            <div
              key={idx}
              className="rounded-xl border border-slate-200 p-5 space-y-4 bg-slate-50/50"
            >
              <div className="flex items-center justify-between">
                <div className="h-5 w-20 rounded bg-slate-200" />
                <div className="flex items-center gap-2">
                  <div className="h-5 w-24 rounded-full bg-slate-200" />
                  <div className="h-5 w-16 rounded-full bg-slate-200" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-5 w-3/4 rounded bg-slate-200" />
                <div className="h-3 w-1/2 rounded bg-slate-100" />
              </div>
              <div className="h-2 w-full rounded-full bg-slate-200" />
              <div className="flex gap-2">
                <div className="h-5 w-24 rounded bg-slate-200" />
                <div className="h-5 w-28 rounded bg-slate-200" />
              </div>
              <div className="h-8 w-full rounded-lg bg-slate-200 pt-2" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  const needsRevisionCount = weakTopics.filter(
    (t) => t.status === "Needs Revision"
  ).length;

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 space-y-5 transition-all">
      {/* Widget Header with Lucide React Icon */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-rose-50 text-rose-600 border border-rose-100 shadow-2xs">
              <Target className="h-5 w-5 text-rose-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Focus & Weak Topics
              </h3>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic diagnostics based on missed tasks, study deficits, and topic mastery
          </p>
        </div>

        {/* Header Summary Pill */}
        {needsRevisionCount > 0 ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-rose-50 px-3 py-1.5 text-xs font-bold text-rose-700 border border-rose-200 self-start sm:self-auto shadow-2xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-600" />
            </span>
            <AlertCircle className="h-3.5 w-3.5 text-rose-600" />
            {needsRevisionCount} {needsRevisionCount === 1 ? "Subject Needs Revision" : "Subjects Need Revision"}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 border border-emerald-200 self-start sm:self-auto">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            All Topics On Track
          </span>
        )}
      </div>

      {/* Main Content: Topics List or Empty State */}
      {weakTopics.length === 0 ? (
        <div className="rounded-xl bg-slate-50/70 p-8 text-center border border-dashed border-slate-200 space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 mb-1 border border-emerald-100">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-bold text-slate-800">No Weak Topics Identified</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            You are completely caught up on all scheduled sessions! When missed tasks or study deficits are detected, deterministic diagnostics will flag topics needing revision here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {weakTopics.map((item) => {
            const isNeedsRevision = item.status === "Needs Revision";
            const planned = item.planned_minutes ?? 0;
            const actual = item.actual_minutes ?? 0;
            const percentCompletion =
              planned > 0
                ? Math.min(100, Math.round((actual / planned) * 100))
                : 0;

            const severityLower = (item.severity || "medium").toLowerCase();

            return (
              <div
                key={item.id}
                className={`flex flex-col justify-between rounded-xl p-5 border transition-all ${
                  isNeedsRevision
                    ? "bg-gradient-to-br from-rose-50/40 via-white to-amber-50/25 border-rose-200 hover:border-rose-300 hover:shadow-xs"
                    : "bg-white border-slate-200 hover:border-slate-300 shadow-2xs"
                }`}
              >
                <div className="space-y-3.5">
                  {/* Top Bar: Subject, Revision Badge & Severity Badge */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {item.subject}
                    </span>

                    <div className="flex items-center gap-1.5">
                      {/* Needs Revision / On Track Badge */}
                      {isNeedsRevision ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-200 shadow-2xs">
                          <AlertCircle className="h-3 w-3 text-rose-600" />
                          Needs Revision
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                          On Track
                        </span>
                      )}

                      {/* Explicit Severity Badge (High / Medium / Low) */}
                      {severityLower === "high" && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-200">
                          High
                        </span>
                      )}
                      {severityLower === "medium" && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                          Medium
                        </span>
                      )}
                      {severityLower === "low" && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                          Low
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Topic Title & Study Hours Summary */}
                  <div>
                    <h4 className="text-base font-bold text-slate-900 leading-snug">
                      {item.topic}
                    </h4>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3 text-slate-400" />
                        Studied: <strong className="text-slate-700">{actual}m</strong> of {planned}m
                      </span>
                      <span>•</span>
                      <span
                        className={
                          percentCompletion < 50
                            ? "text-rose-600 font-semibold"
                            : percentCompletion < 80
                            ? "text-amber-600 font-medium"
                            : "text-emerald-600 font-medium"
                        }
                      >
                        {percentCompletion}% completed
                      </span>
                    </div>
                  </div>

                  {/* Visual Completion Progress Bar */}
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
                      {item.explainability_tags && item.explainability_tags.length > 0 ? (
                        item.explainability_tags.map((tag, tagIdx) => (
                          <span
                            key={tagIdx}
                            className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-0.5 rounded-md bg-amber-50/80 border border-amber-200 text-amber-900 shadow-2xs"
                          >
                            <AlertTriangle className="h-2.5 w-2.5 text-amber-600 shrink-0" />
                            <span>{tag}</span>
                          </span>
                        ))
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                          <Tag className="h-2.5 w-2.5 text-slate-400" />
                          <span>Standard Diagnostic Flag</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Interactive CTA: Find Targeted Resources */}
                <div className="pt-4 mt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <BookOpen className="h-3 w-3 text-slate-400" />
                    Targeted Coursera resources available
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      onSelectTopicForRecommendations(
                        item.recommended_query || `${item.subject} ${item.topic}`
                      )
                    }
                    className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs hover:shadow transition-all cursor-pointer"
                  >
                    <Sparkles className="h-3 w-3 text-indigo-200" />
                    <span>Find Targeted Resources</span>
                    <ArrowRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
