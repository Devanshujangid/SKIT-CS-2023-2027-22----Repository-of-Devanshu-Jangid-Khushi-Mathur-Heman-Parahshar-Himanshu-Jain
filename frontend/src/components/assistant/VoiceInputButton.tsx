
"use client";

import { useEffect } from "react";
import { Mic, MicOff } from "lucide-react";
import { useSpeechRecognition } from "@/lib/useSpeechRecognition";

interface VoiceInputButtonProps {
  onTranscriptChange: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceInputButton({
  onTranscriptChange,
  disabled = false,
}: VoiceInputButtonProps) {
  const {
    transcript,
    isListening,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition();

  useEffect(() => {
    if (transcript) {
      onTranscriptChange(transcript);
    }
  }, [transcript, onTranscriptChange]);

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        title="Speech recognition is not supported in this browser"
        className="rounded-xl border border-slate-200 p-3 text-slate-400"
      >
        <MicOff className="h-5 w-5" />
      </button>
    );
  }

  const handleClick = () => {
    if (isListening) {
      stopListening();
    } else {
      resetTranscript();
      startListening();
    }
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        aria-label={isListening ? "Stop voice input" : "Start voice input"}
        title={isListening ? "Stop listening" : "Start voice input"}
        className={`rounded-xl border p-3 transition-all disabled:opacity-50 ${
          isListening
            ? "animate-pulse border-rose-300 bg-rose-50 text-rose-600"
            : "border-slate-200 bg-white text-indigo-600 hover:bg-indigo-50"
        }`}
      >
        {isListening ? (
          <MicOff className="h-5 w-5" />
        ) : (
          <Mic className="h-5 w-5" />
        )}
      </button>

      {isListening && (
        <span className="text-xs text-rose-600">
          Listening...
        </span>
      )}

      {error && (
  <span
    role="alert"
    aria-live="polite"
    className="max-w-48 text-center text-xs text-rose-600"
  >
    {error}
  </span>
)}
    </div>
  );
}
