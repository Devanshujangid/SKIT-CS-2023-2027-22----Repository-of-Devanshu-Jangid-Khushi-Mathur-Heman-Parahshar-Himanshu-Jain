"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { 
  Send, 
  Mic, 
  MicOff, 
  Loader2, 
  X, 
  Sparkles,
  Volume2
} from "lucide-react";
import { useSpeechRecognition } from "@/lib/useSpeechRecognition";

interface ChatInputFieldProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  initialValue?: string;
}

export default function ChatInputField({
  onSendMessage,
  isLoading = false,
  disabled = false,
  placeholder = "Ask about topics, syllabus, or study timetable...",
  initialValue = "",
}: ChatInputFieldProps) {
  const [input, setInput] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement>(null);

  // Hook into Khushi's Speech Recognition Hook
  const {
    transcript,
    isListening,
    isSupported,
    error: speechError,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition();

  // Keep input in sync with external initialValue if supplied (e.g. from suggestion chip)
  useEffect(() => {
    if (initialValue) {
      setInput(initialValue);
      inputRef.current?.focus();
    }
  }, [initialValue]);

  // Synchronize live speech transcript with the input field
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  // Focus input automatically
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleVoiceToggle = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      resetTranscript();
      startListening();
    }
  }, [isListening, startListening, stopListening, resetTranscript]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading || disabled) return;

    if (isListening) {
      stopListening();
    }

    onSendMessage(trimmed);
    setInput("");
    resetTranscript();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-2">
      {/* Listening Status Indicator Banner */}
      {isListening && (
        <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            </span>
            <span className="font-semibold">Listening to your question...</span>
            <span className="text-[11px] text-rose-500 hidden sm:inline">Speak clearly into microphone</span>
          </div>
          <button
            type="button"
            onClick={stopListening}
            className="text-[11px] font-bold text-rose-600 hover:text-rose-800 underline uppercase tracking-wider"
          >
            Done
          </button>
        </div>
      )}

      {/* Speech Error Banner */}
      {speechError && (
        <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs">
          <span>{speechError}</span>
          <button
            type="button"
            onClick={resetTranscript}
            className="text-slate-400 hover:text-slate-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Main Input Form */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <div className="relative flex-1 flex items-center">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            placeholder={isListening ? "Listening..." : placeholder}
            className={`w-full rounded-xl border bg-slate-50 py-2.5 pl-3.5 pr-8 text-xs sm:text-sm text-slate-800 placeholder-slate-400 transition-all focus:bg-white focus:outline-none focus:ring-2 disabled:opacity-60 ${
              isListening
                ? "border-rose-400 focus:border-rose-500 focus:ring-rose-100 ring-2 ring-rose-100"
                : "border-slate-200 focus:border-indigo-500 focus:ring-indigo-100"
            }`}
          />

          {/* Quick Clear Button */}
          {input.length > 0 && !isLoading && (
            <button
              type="button"
              onClick={() => {
                setInput("");
                resetTranscript();
                inputRef.current?.focus();
              }}
              className="absolute right-2.5 p-1 rounded-md text-slate-400 hover:text-slate-600 transition-colors"
              title="Clear input"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Pulsing Microphone Button for Voice Input */}
        <button
          type="button"
          onClick={handleVoiceToggle}
          disabled={disabled || isLoading || !isSupported}
          aria-label={isListening ? "Stop voice listening" : "Start voice listening"}
          title={
            !isSupported
              ? "Speech recognition is not supported in this browser"
              : isListening
              ? "Stop listening"
              : "Voice input (Speak your question)"
          }
          className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
            isListening
              ? "animate-pulse border-rose-300 bg-rose-50 text-rose-600 ring-4 ring-rose-200/50 shadow-md shadow-rose-200"
              : "border-slate-200 bg-white text-slate-600 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600 shadow-2xs"
          }`}
        >
          {isListening ? (
            <>
              <MicOff className="h-4 w-4" />
              <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-rose-500 ring-2 ring-white" />
            </>
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </button>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!input.trim() || isLoading || disabled}
          aria-label="Send message"
          title="Send message (Enter)"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm shadow-indigo-200 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95 transition-all"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </form>

      {/* Helper Footer */}
      <div className="flex items-center justify-between px-1 text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-indigo-500" />
          Grounded with TF-IDF Coursera catalog
        </span>
        <span className="hidden sm:inline">Press Enter to send • Mic for voice</span>
      </div>
    </div>
  );
}
