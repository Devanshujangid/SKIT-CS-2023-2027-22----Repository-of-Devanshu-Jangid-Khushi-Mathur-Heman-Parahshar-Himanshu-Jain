"use client";

import { useState, useRef, useEffect } from "react";
import { 
  X, 
  Send, 
  Sparkles, 
  Bot, 
  User, 
  BookOpen, 
  Calendar, 
  Clock, 
  CheckCircle2, 
  RotateCcw 
} from "lucide-react";

export interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
}

interface AiAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: "msg-1",
    sender: "ai",
    text: "Hello Devanshu! 👋 I'm your AI Academic Assistant. I'm connected to your syllabus and study timetable. How can I assist you with your prep today?",
    timestamp: "10:30 AM",
  },
  {
    id: "msg-2",
    sender: "user",
    text: "Why is 'Process Synchronization' flagged under Needs Revision?",
    timestamp: "10:31 AM",
  },
  {
    id: "msg-3",
    sender: "ai",
    text: "Based on your diagnostic telemetry, 'Process Synchronization' had 90 planned minutes on Wednesday, but 0 minutes were logged (Rule 1: Missed Task, Study Deficit: -90m). Would you like to review Peterson's Algorithm or re-balance this into Saturday's catch-up slot?",
    timestamp: "10:32 AM",
  },
];

const SUGGESTIONS = [
  "Explain Peterson's Solution",
  "How to recover missed OS session?",
  "Review high-priority exam targets",
  "Summarize my weekly study pace",
];

export default function AiAssistantDrawer({ isOpen, onClose }: AiAssistantDrawerProps) {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      setTimeout(() => inputRef.current?.focus(), 250);
    }
  }, [messages, isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleSend = (textToSend?: string) => {
    const query = (textToSend ?? input).trim();
    if (!query) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!textToSend) setInput("");
    setIsTyping(true);

    // Simulate smart AI response tailored to course topics
    setTimeout(() => {
      let replyText = "";
      const lower = query.toLowerCase();

      if (lower.includes("peterson") || lower.includes("synchronization")) {
        replyText = "Peterson's algorithm is a classical concurrent programming solution for mutual exclusion in two-process critical section problems. It guarantees Mutual Exclusion, Progress, and Bounded Waiting using a `flag[2]` boolean array and a shared `turn` variable.";
      } else if (lower.includes("recover") || lower.includes("rebalance") || lower.includes("missed")) {
        replyText = "The Adaptive Planner has automatically queued your missed session with a 'Catch-up: Process Synchronization' prefix. Click 'Rebalance Schedule' in your dashboard banner to lock it into your upcoming schedule without exceeding your daily 4.5h ceiling.";
      } else if (lower.includes("exam") || lower.includes("target")) {
        replyText = "You have the Mid-Term OS Exam in 4 days. High Priority Targets: 1. Process Synchronization (-90m deficit), 2. Virtual Memory Paging, 3. Deadlock Detection & Banker's Algorithm.";
      } else if (lower.includes("pace") || lower.includes("velocity") || lower.includes("hours")) {
        replyText = "Your current weekly adherence rate is 89% (30.8 hours logged out of 34.5 planned). You're on track for an 8.5+ CGPA milestone!";
      } else {
        replyText = `I understand you're asking about "${query}". I'm cross-referencing your course syllabus and Coursera resource catalog to recommend targeted study blocks.`;
      }

      const aiResponse: Message = {
        id: `ai-${Date.now()}`,
        sender: "ai",
        text: replyText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, aiResponse]);
      setIsTyping(false);
    }, 600);
  };

  const handleReset = () => {
    setMessages(INITIAL_MESSAGES);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs transition-opacity duration-300 ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sliding Drawer */}
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-full sm:w-[420px] md:w-[460px] bg-white shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="AI Study Assistant"
      >
        {/* Fixed Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-linear-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/90 text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="h-5 w-5" />
              <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-slate-900 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm tracking-tight text-white">Smart AI Assistant</h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  Gemini Flash
                </span>
              </div>
              <p className="text-xs text-slate-300">Deterministic Schedule & Topic Guidance</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleReset}
              title="Reset conversation"
              className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Close chat"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Suggestion Chips */}
        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0">
          <span className="text-[11px] font-semibold text-slate-500 shrink-0">Try:</span>
          {SUGGESTIONS.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(item)}
              className="text-[11px] whitespace-nowrap bg-white hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 px-2.5 py-1 rounded-full border border-slate-200 hover:border-indigo-200 font-medium transition-colors"
            >
              {item}
            </button>
          ))}
        </div>

        {/* Scrollable Message Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
          {messages.map((msg) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={msg.id}
                className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg text-xs font-bold ${
                    isUser
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-indigo-600 border border-slate-200 shadow-2xs"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div className={`max-w-[80%] space-y-1 ${isUser ? "items-end text-right" : "items-start text-left"}`}>
                  <div
                    className={`rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed shadow-xs ${
                      isUser
                        ? "bg-indigo-600 text-white rounded-tr-xs"
                        : "bg-white text-slate-800 border border-slate-200/80 rounded-tl-xs"
                    }`}
                  >
                    {msg.text}
                  </div>
                  <span className="text-[10px] text-slate-400 font-medium px-1">
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex items-start gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-indigo-600 border border-slate-200 shadow-2xs">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl rounded-tl-xs bg-white border border-slate-200/80 px-4 py-2.5 shadow-xs">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Field */}
        <div className="p-3.5 border-t border-slate-200 bg-white shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about topics, timetable, or exams..."
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-all"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm shadow-indigo-200 transition-all"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 px-1">
            <span>Deterministic grounded guidance</span>
            <span>Press Enter to send</span>
          </div>
        </div>
      </aside>
    </>
  );
}
