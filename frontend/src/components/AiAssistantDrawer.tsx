"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { 
  X, 
  Sparkles, 
  RotateCcw, 
  Bot, 
  Lightbulb
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import ChatMessageBubble, { ChatMessage } from "@/components/assistant/ChatMessageBubble";
import ChatInputField from "@/components/assistant/ChatInputField";
import { detectAssistantVoiceCommand } from "@/lib/assistantVoiceCommands";

interface AiAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "msg-welcome-1",
    sender: "ai",
    text: "Hello Devanshu! 👋 I'm your Smart Learning Assistant. I'm connected to your Operating Systems syllabus and Coursera resource catalog. How can I assist your study prep today?",
    keyPoints: [
      "Ask questions about complex academic concepts",
      "Get grounded Coursera course recommendations",
      "Use voice transcription with the microphone button",
    ],
    timestamp: "10:30 AM",
  },
  {
    id: "msg-sample-user",
    sender: "user",
    text: "Why is 'Process Synchronization' flagged under Needs Revision?",
    timestamp: "10:31 AM",
  },
  {
    id: "msg-sample-ai",
    sender: "ai",
    text: "Based on your diagnostic telemetry, 'Process Synchronization' had 90 planned minutes on Wednesday, but 0 minutes were logged (Rule 1: Missed Task, Study Deficit: -90m). Peterson's Solution and Semaphores are critical exam targets for Unit 2.",
    keyPoints: [
      "Critical section requires Mutual Exclusion, Progress, and Bounded Waiting",
      "Peterson's Algorithm uses turn and flag[2] variables for two-process synchronization",
    ],
    followUpSuggestion: "Explain Peterson's algorithm step by step",
    recommendations: [
      {
        "Course Name": "Operating Systems and You: Becoming a Power User",
        "University": "Google",
        "Difficulty Level": "Beginner",
        "Course Rating": 4.8,
        "Course URL": "https://www.coursera.org/learn/operating-systems",
        similarity_score: 0.4585,
      },
    ],
    timestamp: "10:32 AM",
  },
];

const QUICK_SUGGESTIONS = [
  "Explain Peterson's Solution",
  "How to recover missed OS session?",
  "Deadlock prevention vs avoidance",
  "What are Semaphores in OS?",
];

export default function AiAssistantDrawer({ isOpen, onClose }: AiAssistantDrawerProps) {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingSuggestion, setPendingSuggestion] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, isOpen]);

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

  // Direct Live Wiring to Heman's POST /api/v1/chat endpoint (with fallback to /api/v1/ai/chat)
  const handleSendMessage = useCallback(async (messageText: string) => {
    const query = messageText.trim();
    if (!query) return;

    // Sprint 9: Voice Assistant navigation commands
const detectedCommand = detectAssistantVoiceCommand(query);

let commandResponse: string | null = null;

if (detectedCommand === "leaderboard") {
  commandResponse =
    "Your leaderboard rank is currently unavailable. I don't have verified leaderboard data yet, so I won't guess your rank.";
} else if (detectedCommand === "goal") {
  commandResponse =
    "Your academic goals are saved in your profile, but I don't have verified goal achievement data yet. I cannot confirm whether your goal has been achieved.";
}
    if (commandResponse) {
  const assistantMessage: ChatMessage = {
    id: `ai-command-${Date.now()}`,
    sender: "ai",
    text: commandResponse,
    timestamp: new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  };

  setMessages((prev) => [...prev, assistantMessage]);
  return;
}
    setIsLoading(true);
    setPendingSuggestion("");

    try {
      const token = await getToken();

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // Try primary endpoint POST /api/v1/chat first, fallback to POST /api/v1/ai/chat
      let response: Response;
      try {
        response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
          method: "POST",
          headers,
          body: JSON.stringify({ message: query, stream: true }),
        });

        if (response.status === 404) {
          response = await fetch(`${API_BASE_URL}/api/v1/ai/chat`, {
            method: "POST",
            headers,
            body: JSON.stringify({ message: query, stream: true }),
          });
        }
      } catch {
        // Fallback endpoint probe
        response = await fetch(`${API_BASE_URL}/api/v1/ai/chat`, {
          method: "POST",
          headers,
          body: JSON.stringify({ message: query, stream: true }),
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("text/event-stream") && response.body) {
        // Real-time token streaming (ChatGPT-style)
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const aiMessageId = `ai-${Date.now()}`;
        let accumulatedText = "";

        const initialAiMessage: ChatMessage = {
          id: aiMessageId,
          sender: "ai",
          text: "",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setMessages((prev) => [...prev, initialAiMessage]);
        setIsLoading(false);

        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed.startsWith("data:")) continue;
            const dataStr = trimmed.replace(/^data:\s*/, "").trim();
            if (dataStr === "[DONE]") break;

            try {
              const eventData = JSON.parse(dataStr);
              if (eventData.type === "content" && eventData.delta) {
                accumulatedText += eventData.delta;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId ? { ...msg, text: accumulatedText } : msg
                  )
                );
              } else if (eventData.type === "refusal") {
                accumulatedText = eventData.refusal_message || "This query falls outside your academic curriculum.";
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? {
                          ...msg,
                          text: accumulatedText,
                          keyPoints: eventData.suggested_academic_topics || [],
                        }
                      : msg
                  )
                );
              } else if (eventData.type === "metadata" && Array.isArray(eventData.recommendations)) {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? { ...msg, recommendations: eventData.recommendations }
                      : msg
                  )
                );
              } else if (eventData.type === "error") {
                accumulatedText = eventData.detail || "Error generating response.";
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId ? { ...msg, text: accumulatedText, isError: true } : msg
                  )
                );
              }
            } catch {
              // Ignore partial JSON parse errors
            }
          }
        }
      } else {
        // Standard JSON response fallback
        const data = await response.json();

        const aiMessage: ChatMessage = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: data.explanation || data.message || "Here is the explanation for your topic:",
          keyPoints: Array.isArray(data.key_points) ? data.key_points : [],
          followUpSuggestion: data.follow_up_suggestion || undefined,
          recommendations: Array.isArray(data.recommendations) ? data.recommendations : [],
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setMessages((prev) => [...prev, aiMessage]);
      }
    } catch (err: unknown) {
      console.warn("API chat request failed, generating contextual fallback:", err);

      // Graceful offline fallback explanation so student experience is never broken
      let fallbackText = "I encountered a network issue contacting the live AI chat service. ";
      const lower = query.toLowerCase();

      if (lower.includes("peterson")) {
        fallbackText += "Peterson's algorithm is a classical concurrent programming solution for mutual exclusion in two-process critical section problems. It guarantees Mutual Exclusion, Progress, and Bounded Waiting using a flag[2] array and shared turn variable.";
      } else if (lower.includes("recover") || lower.includes("missed") || lower.includes("rebalance")) {
        fallbackText += "Your missed sessions are automatically flagged with 'Catch-up' prefixes. You can click 'Rebalance Schedule' on your dashboard banner to redistribute them forward.";
      } else if (lower.includes("deadlock")) {
        fallbackText += "Deadlock prevention eliminates at least one of Coffman's four conditions (Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait). Deadlock avoidance uses Banker's Algorithm to verify safe states dynamically.";
      } else if (lower.includes("semaphore")) {
        fallbackText += "A Semaphore is an integer variable used for process synchronization accessed only through wait() [P] and signal() [V] atomic operations.";
      } else {
        fallbackText += `Here is guidance for "${query}": review standard course reference materials and the Coursera catalog for Unit 2 exam preparation.`;
      }

      const errorMessage: ChatMessage = {
        id: `ai-err-${Date.now()}`,
        sender: "ai",
        text: fallbackText,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  const handleReset = () => {
    setMessages(INITIAL_MESSAGES);
    setPendingSuggestion("");
  };

  const handleRetryLast = () => {
    // Find the last user message and resend it
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === "user") {
        handleSendMessage(messages[i].text);
        break;
      }
    }
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

      {/* Sliding Drawer: Mobile spans w-full, tablet/desktop fixed sm:w-[400px] md:w-[420px] */}
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-full sm:w-[400px] md:w-[420px] max-w-full bg-white shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="AI Academic Assistant"
      >
        {/* Fixed Header */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 sm:py-4 border-b border-slate-200 bg-linear-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shrink-0">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div className="relative flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-xl bg-indigo-600/90 text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="h-4 w-4 sm:h-5 sm:w-5" />
              <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-slate-900 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 sm:gap-2">
                <h3 className="font-bold text-xs sm:text-sm tracking-tight text-white">Smart AI Assistant</h3>
                <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  Live API + Voice
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-300">Wired to POST /api/v1/chat & Speech</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleReset}
              title="Reset conversation"
              className="p-2 sm:p-1.5 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 sm:p-1.5 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              aria-label="Close chat"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Suggestion Chips: horizontally scrollable and touch-friendly */}
        <div className="px-3 sm:px-4 py-2 sm:py-2.5 bg-slate-50 border-b border-slate-100 flex items-center gap-1.5 overflow-x-auto scrollbar-none touch-pan-x shrink-0">
          <span className="text-[11px] font-semibold text-slate-500 shrink-0 flex items-center gap-1">
            <Lightbulb className="h-3 w-3 text-amber-500" />
            Try:
          </span>
          {QUICK_SUGGESTIONS.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendMessage(item)}
              className="text-[11px] whitespace-nowrap bg-white hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 px-2.5 py-1 rounded-full border border-slate-200 hover:border-indigo-200 font-medium transition-colors cursor-pointer active:scale-95"
            >
              {item}
            </button>
          ))}
        </div>

        {/* Scrollable Message Area: No horizontal overflow */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 space-y-3 sm:space-y-4 bg-slate-50/50">
          {messages.map((msg) => (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              onSelectSuggestion={(suggestion) => handleSendMessage(suggestion)}
              onRetry={handleRetryLast}
            />
          ))}

          {/* Typing Indicator while waiting for live API response */}
          {isLoading && (
            <div className="flex items-start gap-2.5 animate-in fade-in duration-200">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-indigo-500 to-violet-600 text-white shadow-2xs">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl rounded-tl-xs bg-white border border-slate-200/90 px-3.5 py-2.5 sm:px-4 sm:py-3 shadow-xs">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-bounce" />
                  <span className="ml-2 text-[11px] sm:text-xs text-slate-400 font-medium">
                    Consulting Gemini & Coursera catalog...
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Area with Connected Voice Transcription */}
        <div className="p-2.5 sm:p-3.5 border-t border-slate-200 bg-white shrink-0">
          <ChatInputField
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            initialValue={pendingSuggestion}
          />
        </div>
      </aside>
    </>
  );
}
