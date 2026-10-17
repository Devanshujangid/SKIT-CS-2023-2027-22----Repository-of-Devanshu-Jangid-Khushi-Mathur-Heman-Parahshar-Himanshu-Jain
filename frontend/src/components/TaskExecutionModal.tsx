"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
  BookOpen,
  Calendar,
  FileText,
  Loader2,
  ChevronRight,
  RotateCcw,
} from "lucide-react";

export type TaskExecutionStatus = "completed" | "partially_completed" | "missed";

export interface TaskExecutionData {
  status: TaskExecutionStatus;
  actual_minutes: number;
  notes?: string;
  updated_at?: string;
}

export interface TaskModalItem {
  id: string;
  subject: string;
  topic: string;
  activity: string;
  duration_minutes: number;
  priority: "high" | "medium" | "low";
  completed?: boolean;
  execution?: TaskExecutionData;
}

interface TaskExecutionModalProps {
  isOpen: boolean;
  task: TaskModalItem | null;
  onClose: () => void;
  onSave: (taskId: string, execution: TaskExecutionData) => Promise<void>;
  isSaving?: boolean;
}

export default function TaskExecutionModal({
  isOpen,
  task,
  onClose,
  onSave,
  isSaving = false,
}: TaskExecutionModalProps) {
  const [status, setStatus] = useState<TaskExecutionStatus>("completed");
  const [actualMinutes, setActualMinutes] = useState<number>(60);
  const [notes, setNotes] = useState<string>("");

  useEffect(() => {
    if (task) {
      if (task.execution) {
        setStatus(task.execution.status);
        setActualMinutes(
          task.execution.actual_minutes ??
            (task.execution.status === "missed" ? 0 : task.duration_minutes)
        );
        setNotes(task.execution.notes || "");
      } else if (task.completed) {
        setStatus("completed");
        setActualMinutes(task.duration_minutes);
        setNotes("");
      } else {
        setStatus("completed");
        setActualMinutes(task.duration_minutes);
        setNotes("");
      }
    }
  }, [task]);

  if (!isOpen || !task) return null;

  const plannedMinutes = task.duration_minutes || 60;

  const handleStatusChange = (newStatus: TaskExecutionStatus) => {
    setStatus(newStatus);
    if (newStatus === "completed") {
      setActualMinutes(plannedMinutes);
    } else if (newStatus === "partially_completed") {
      // Default to half of planned duration or current actual if non-zero
      setActualMinutes((prev) => (prev > 0 && prev < plannedMinutes ? prev : Math.max(15, Math.round(plannedMinutes / 2))));
    } else if (newStatus === "missed") {
      setActualMinutes(0);
    }
  };

  const handleMinutesChange = (delta: number) => {
    setActualMinutes((prev) => Math.max(0, Math.min(600, prev + delta)));
  };

  const handleSetPreset = (mins: number) => {
    setActualMinutes(mins);
    if (mins === 0) {
      setStatus("missed");
    } else if (mins < plannedMinutes) {
      setStatus("partially_completed");
    } else {
      setStatus("completed");
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave(task.id, {
      status,
      actual_minutes: actualMinutes,
      notes: notes.trim() || undefined,
    });
  };

  const percentStudied = plannedMinutes > 0 ? Math.round((actualMinutes / plannedMinutes) * 100) : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="task-execution-title"
    >
      <div
        className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl border border-slate-100 transition-all sm:my-8 animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with gradient subtle background */}
        <div className="relative border-b border-slate-100 bg-gradient-to-r from-indigo-50/50 via-white to-slate-50 p-6 pb-5">
          <button
            type="button"
            onClick={onClose}
            className="absolute top-5 right-5 rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold tracking-wide uppercase bg-indigo-100 text-indigo-700">
              {task.subject}
            </span>
            <span className="text-xs font-medium text-slate-400">• {task.activity}</span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                task.priority === "high"
                  ? "bg-rose-50 text-rose-600 border border-rose-200"
                  : task.priority === "medium"
                  ? "bg-amber-50 text-amber-600 border border-amber-200"
                  : "bg-emerald-50 text-emerald-600 border border-emerald-200"
              }`}
            >
              {task.priority} Priority
            </span>
          </div>

          <h3 id="task-execution-title" className="text-xl font-bold text-slate-900">
            {task.topic}
          </h3>

          <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
            <Clock className="h-3.5 w-3.5 text-slate-400" />
            <span>Planned Duration: <strong>{plannedMinutes} minutes</strong></span>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleFormSubmit} className="p-6 space-y-6">
          {/* Status Selection Cards */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2.5">
              Execution Status <span className="text-rose-500">*</span>
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Option: Completed */}
              <button
                type="button"
                onClick={() => handleStatusChange("completed")}
                className={`relative flex flex-col items-start p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  status === "completed"
                    ? "border-emerald-500 bg-emerald-50/70 shadow-sm ring-1 ring-emerald-500 text-emerald-900"
                    : "border-slate-200 hover:border-slate-300 bg-white text-slate-700"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <CheckCircle2
                    className={`h-5 w-5 ${
                      status === "completed" ? "text-emerald-600" : "text-slate-400"
                    }`}
                  />
                  {status === "completed" && (
                    <span className="text-[10px] font-bold uppercase bg-emerald-600 text-white px-1.5 py-0.5 rounded">
                      Selected
                    </span>
                  )}
                </div>
                <span className="text-sm font-bold">Completed</span>
                <span className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                  Covered full planned session
                </span>
              </button>

              {/* Option: Partially Completed */}
              <button
                type="button"
                onClick={() => handleStatusChange("partially_completed")}
                className={`relative flex flex-col items-start p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  status === "partially_completed"
                    ? "border-amber-500 bg-amber-50/70 shadow-sm ring-1 ring-amber-500 text-amber-900"
                    : "border-slate-200 hover:border-slate-300 bg-white text-slate-700"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <Clock
                    className={`h-5 w-5 ${
                      status === "partially_completed" ? "text-amber-600" : "text-slate-400"
                    }`}
                  />
                  {status === "partially_completed" && (
                    <span className="text-[10px] font-bold uppercase bg-amber-600 text-white px-1.5 py-0.5 rounded">
                      Selected
                    </span>
                  )}
                </div>
                <span className="text-sm font-bold">Partial</span>
                <span className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                  Studied part of the session
                </span>
              </button>

              {/* Option: Missed */}
              <button
                type="button"
                onClick={() => handleStatusChange("missed")}
                className={`relative flex flex-col items-start p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  status === "missed"
                    ? "border-rose-500 bg-rose-50/70 shadow-sm ring-1 ring-rose-500 text-rose-900"
                    : "border-slate-200 hover:border-slate-300 bg-white text-slate-700"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <AlertCircle
                    className={`h-5 w-5 ${
                      status === "missed" ? "text-rose-600" : "text-slate-400"
                    }`}
                  />
                  {status === "missed" && (
                    <span className="text-[10px] font-bold uppercase bg-rose-600 text-white px-1.5 py-0.5 rounded">
                      Selected
                    </span>
                  )}
                </div>
                <span className="text-sm font-bold">Missed</span>
                <span className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                  Did not study this session
                </span>
              </button>
            </div>
          </div>

          {/* Exact Study Minutes Input Section */}
          <div className="rounded-xl bg-slate-50 p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label
                  htmlFor="actual-minutes-input"
                  className="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Exact Study Minutes
                </label>
                <p className="text-xs text-slate-500 mt-0.5">
                  Record exact time dedicated to this session
                </p>
              </div>

              {/* Percentage Badge */}
              <div
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                  percentStudied >= 100
                    ? "bg-emerald-100 text-emerald-800"
                    : percentStudied >= 50
                    ? "bg-amber-100 text-amber-800"
                    : percentStudied > 0
                    ? "bg-orange-100 text-orange-800"
                    : "bg-slate-200 text-slate-700"
                }`}
              >
                {percentStudied}% of target
              </div>
            </div>

            {/* Minutes Stepper & Direct Input */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleMinutesChange(-15)}
                className="rounded-lg bg-white border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-95 transition-all"
                title="Subtract 15 minutes"
              >
                -15m
              </button>
              <button
                type="button"
                onClick={() => handleMinutesChange(-5)}
                className="rounded-lg bg-white border border-slate-200 px-2.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-95 transition-all"
                title="Subtract 5 minutes"
              >
                -5m
              </button>

              <div className="relative flex-1">
                <input
                  id="actual-minutes-input"
                  type="number"
                  min="0"
                  max="600"
                  value={actualMinutes}
                  onChange={(e) => {
                    const val = Math.max(0, parseInt(e.target.value, 10) || 0);
                    setActualMinutes(val);
                    if (val === 0) setStatus("missed");
                    else if (val < plannedMinutes) setStatus("partially_completed");
                    else setStatus("completed");
                  }}
                  className="w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-center text-lg font-bold text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                />
                <span className="absolute right-3 top-2.5 text-xs font-semibold text-slate-400 pointer-events-none">
                  mins
                </span>
              </div>

              <button
                type="button"
                onClick={() => handleMinutesChange(+5)}
                className="rounded-lg bg-white border border-slate-200 px-2.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-95 transition-all"
                title="Add 5 minutes"
              >
                +5m
              </button>
              <button
                type="button"
                onClick={() => handleMinutesChange(+15)}
                className="rounded-lg bg-white border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-95 transition-all"
                title="Add 15 minutes"
              >
                +15m
              </button>
            </div>

            {/* Quick Presets */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] font-semibold text-slate-400 mr-1">Presets:</span>
              <button
                type="button"
                onClick={() => handleSetPreset(0)}
                className={`rounded-md px-2 py-0.5 text-xs font-medium border transition-colors ${
                  actualMinutes === 0
                    ? "bg-slate-800 text-white border-slate-800"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                0m (Missed)
              </button>
              <button
                type="button"
                onClick={() => handleSetPreset(Math.round(plannedMinutes * 0.25))}
                className="rounded-md px-2 py-0.5 text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                {Math.round(plannedMinutes * 0.25)}m (25%)
              </button>
              <button
                type="button"
                onClick={() => handleSetPreset(Math.round(plannedMinutes * 0.5))}
                className="rounded-md px-2 py-0.5 text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                {Math.round(plannedMinutes * 0.5)}m (50%)
              </button>
              <button
                type="button"
                onClick={() => handleSetPreset(plannedMinutes)}
                className={`rounded-md px-2 py-0.5 text-xs font-medium border transition-colors ${
                  actualMinutes === plannedMinutes
                    ? "bg-emerald-600 text-white border-emerald-600"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {plannedMinutes}m (Full Target)
              </button>
            </div>
          </div>

          {/* Optional Reflection / Notes Field */}
          <div>
            <label
              htmlFor="session-notes"
              className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5"
            >
              Session Notes & Reflection <span className="text-slate-400 text-normal">(Optional)</span>
            </label>
            <textarea
              id="session-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Completed questions 1-5, got stuck on semaphore synchronization..."
              className="w-full rounded-xl border border-slate-200 p-3 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="rounded-xl px-4 py-2.5 text-xs sm:text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 active:scale-95 transition-all cursor-pointer disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Saving Execution...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Save Execution</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
