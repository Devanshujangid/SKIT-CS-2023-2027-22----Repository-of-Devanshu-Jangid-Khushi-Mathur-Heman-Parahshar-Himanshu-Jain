
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface SpeechRecognitionResult {
  transcript: string;
  isListening: boolean;
  isSupported: boolean;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: {
        transcript: string;
      };
    };
  };
}

interface SpeechRecognitionErrorEvent {
  error: string;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
}

export function normalizeTechnicalTerms(text: string): string {
  const technicalTerms: [RegExp, string][] = [
    [/\bpostgre\s*sql\b/gi, "PostgreSQL"],
    [/\bpostgres(?:\s*sql)?\b/gi, "PostgreSQL"],
    [/\bnext\s*\.?\s*js\b/gi, "Next.js"],
    [/\bfast\s+a\s+p\s+i\b/gi, "FastAPI"],
    [/\bfast\s*api\b/gi, "FastAPI"],
    [/\bsuper\s*base\b/gi, "Supabase"],
    [/\bgit\s*hub\b/gi, "GitHub"],
    [/\btype\s*script\b/gi, "TypeScript"],
    [/\bjava\s*script\b/gi, "JavaScript"],
    [/\bg\s+mini\b/gi, "Gemini"],
    [/\bgemini\b/gi, "Gemini"],
    [/\bnode\s*\.?\s*js\b/gi, "Node.js"],
    [/\bmy\s*sql\b/gi, "MySQL"],
    [/\bmongo\s*db\b/gi, "MongoDB"],
    [/\bvs\s+code\b/gi, "VS Code"],
  ];

  return technicalTerms.reduce(
    (normalizedText, [pattern, replacement]) =>
      normalizedText.replace(pattern, replacement),
    text
  );
}

export function useSpeechRecognition(): SpeechRecognitionResult {
  const [transcript, setTranscript] = useState("");
  const [isListening, setIsListening] = useState(false);

  const [isSupported] = useState(() => {
    if (typeof window === "undefined") return false;

    return (
      "SpeechRecognition" in window ||
      "webkitSpeechRecognition" in window
    );
  });

  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  useEffect(() => {
    const browserWindow = window as SpeechRecognitionWindow;

    const SpeechRecognition =
      browserWindow.SpeechRecognition ||
      browserWindow.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-IN";

    recognition.onresult = (event) => {
      let currentTranscript = "";

      for (let i = 0; i < event.results.length; i++) {
        currentTranscript +=
          event.results[i][0].transcript + " ";
      }

       const normalizedTranscript = normalizeTechnicalTerms(
    currentTranscript.trim()
  );

      setTranscript(normalizedTranscript);
    };

    recognition.onerror = (event) => {
      const errorMessages: Record<string, string> = {
        "not-allowed": "Microphone permission denied. Please allow microphone access.",
        "no-speech": "No speech detected. Please try again.",
        "audio-capture": "No microphone was found.",
        network: "Network error. Please check your internet connection.",
        aborted: "Speech recognition was interrupted.",
      };

      setError(
        errorMessages[event.error] ||
          "Speech recognition failed. Please try again."
      );

      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
      recognitionRef.current = null;
    };
  }, []);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;

    try {
      setError(null);
      recognitionRef.current.start();
      setIsListening(true);
    } catch {
      setError("Unable to start microphone. Please try again.");
      setIsListening(false);
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript("");
    setError(null);
  }, []);

  return {
    transcript,
    isListening,
    isSupported,
    error,
    startListening,
    stopListening,
    resetTranscript,
  };
}
