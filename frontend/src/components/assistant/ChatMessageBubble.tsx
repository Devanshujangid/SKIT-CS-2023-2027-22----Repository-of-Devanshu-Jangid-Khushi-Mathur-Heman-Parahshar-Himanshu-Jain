"use client";

import { 
  Bot, 
  User, 
  CheckCircle2, 
  ArrowRight, 
  ExternalLink, 
  BookOpen, 
  Sparkles, 
  RotateCcw, 
  AlertCircle,
  GraduationCap
} from "lucide-react";

export interface ChatCourseRecommendation {
  "Course Name": string;
  "Course Description"?: string;
  "Skills"?: string;
  "University"?: string;
  "Difficulty Level"?: string;
  "Course Rating"?: number | string;
  "Course URL"?: string;
  similarity_score?: number;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  keyPoints?: string[];
  followUpSuggestion?: string;
  recommendations?: ChatCourseRecommendation[];
  timestamp: string;
  isError?: boolean;
}

interface ChatMessageBubbleProps {
  message: ChatMessage;
  onSelectSuggestion?: (suggestion: string) => void;
  onRetry?: () => void;
}

export default function ChatMessageBubble({
  message,
  onSelectSuggestion,
  onRetry,
}: ChatMessageBubbleProps) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`flex items-start gap-2.5 sm:gap-3 ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl text-xs font-bold transition-all ${
          isUser
            ? "bg-indigo-600 text-white shadow-xs shadow-indigo-300"
            : message.isError
            ? "bg-rose-100 text-rose-600 border border-rose-200"
            : "bg-linear-to-br from-indigo-500 to-violet-600 text-white shadow-xs shadow-indigo-200"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : message.isError ? (
          <AlertCircle className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>

      {/* Message Content Container */}
      <div
        className={`max-w-[85%] sm:max-w-[82%] space-y-2 ${
          isUser ? "items-end text-right" : "items-start text-left"
        }`}
      >
        {/* Main Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed shadow-xs transition-all ${
            isUser
              ? "bg-indigo-600 text-white rounded-tr-xs"
              : message.isError
              ? "bg-rose-50 border border-rose-200 text-rose-900 rounded-tl-xs"
              : "bg-white border border-slate-200/90 text-slate-800 rounded-tl-xs"
          }`}
        >
          {/* Text paragraph */}
          <div className="whitespace-pre-wrap">{message.text}</div>

          {/* Key Points Section (if returned by backend) */}
          {message.keyPoints && message.keyPoints.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                Key Takeaways
              </span>
              <ul className="space-y-1 mt-1 text-slate-700 text-xs">
                {message.keyPoints.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Grounded Coursera Recommendations Cards */}
          {message.recommendations && message.recommendations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-700">
                <span className="flex items-center gap-1 text-indigo-700 uppercase tracking-wider">
                  <BookOpen className="h-3 w-3" />
                  Grounded Coursera Courses ({message.recommendations.length})
                </span>
                <span className="text-[10px] text-slate-400 font-normal">
                  TF-IDF Cosine Match
                </span>
              </div>

              <div className="space-y-2">
                {message.recommendations.slice(0, 3).map((course, idx) => {
                  const rating = course["Course Rating"];
                  const difficulty = course["Difficulty Level"];
                  const university = course["University"];
                  const score = course.similarity_score;
                  const url = course["Course URL"];

                  return (
                    <div
                      key={idx}
                      className="group rounded-xl border border-slate-200/90 bg-slate-50/70 p-2.5 hover:bg-indigo-50/40 hover:border-indigo-200 transition-all text-left"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-xs text-slate-900 group-hover:text-indigo-700 line-clamp-1 transition-colors">
                            {course["Course Name"]}
                          </p>
                          {university && (
                            <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5 flex items-center gap-1">
                              <GraduationCap className="h-3 w-3 text-slate-400 shrink-0" />
                              <span>{university}</span>
                            </p>
                          )}
                        </div>
                        {url && (
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-indigo-600 hover:border-indigo-300 shadow-2xs transition-all shrink-0"
                            title="Open course on Coursera"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>

                      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                        {difficulty && (
                          <span className="rounded-md bg-white border border-slate-200 px-1.5 py-0.5 font-medium text-slate-600">
                            {difficulty}
                          </span>
                        )}
                        {rating && (
                          <span className="rounded-md bg-amber-50 border border-amber-200 px-1.5 py-0.5 font-semibold text-amber-700">
                            ★ {rating}
                          </span>
                        )}
                        {typeof score === "number" && (
                          <span className="rounded-md bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 font-semibold text-emerald-700 ml-auto">
                            {Math.round(score * 100)}% match
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Follow-up Suggestion Chip */}
          {message.followUpSuggestion && onSelectSuggestion && (
            <div className="mt-3 pt-2.5 border-t border-slate-100">
              <button
                type="button"
                onClick={() => onSelectSuggestion(message.followUpSuggestion!)}
                className="w-full text-left inline-flex items-center justify-between gap-2 rounded-xl bg-indigo-50/80 hover:bg-indigo-100/90 border border-indigo-200 px-3 py-2 text-xs font-medium text-indigo-800 transition-all group"
              >
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[10px] uppercase font-bold text-indigo-500 shrink-0">Next:</span>
                  <span className="truncate">{message.followUpSuggestion}</span>
                </div>
                <ArrowRight className="h-3.5 w-3.5 text-indigo-600 group-hover:translate-x-0.5 transition-transform shrink-0" />
              </button>
            </div>
          )}

          {/* Retry Button on Error */}
          {message.isError && onRetry && (
            <div className="mt-2.5 pt-2 border-t border-rose-200/60">
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 hover:text-rose-900 transition-colors"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Retry Request</span>
              </button>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`px-1 text-[10px] font-medium text-slate-400 ${isUser ? "text-right" : "text-left"}`}>
          {message.timestamp}
        </div>
      </div>
    </div>
  );
}
