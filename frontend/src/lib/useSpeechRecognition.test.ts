
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import {
  useSpeechRecognition,
  normalizeTechnicalTerms,
} from "./useSpeechRecognition";

type MockResultEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      0: { transcript: string };
      isFinal: boolean;
    };
  };
};

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = [];

  continuous = false;
  interimResults = false;
  lang = "";

  onresult: ((event: MockResultEvent) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;

  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }
}

function getRecognition(): MockSpeechRecognition {
  const instance = MockSpeechRecognition.instances.at(-1);

  if (!instance) {
    throw new Error("SpeechRecognition instance not found");
  }

  return instance;
}

beforeEach(() => {
  MockSpeechRecognition.instances = [];

  Object.defineProperty(window, "SpeechRecognition", {
    configurable: true,
    value: MockSpeechRecognition,
  });
});

afterEach(() => {
  delete (window as Window & {
    SpeechRecognition?: unknown;
  }).SpeechRecognition;

  delete (window as Window & {
    webkitSpeechRecognition?: unknown;
  }).webkitSpeechRecognition;

  vi.clearAllMocks();
});

describe("useSpeechRecognition", () => {
  it("should initialize when speech recognition is supported", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    expect(result.current.isSupported).toBe(true);
    expect(result.current.isListening).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("should handle microphone permission denial", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      result.current.startListening();
    });

    expect(result.current.isListening).toBe(true);

    act(() => {
      getRecognition().onerror?.({ error: "not-allowed" });
    });

    expect(result.current.isListening).toBe(false);
    expect(result.current.error).toBe(
      "Microphone permission denied. Please allow microphone access."
    );
  });

  it("should handle no-speech error", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      getRecognition().onerror?.({ error: "no-speech" });
    });

    expect(result.current.error).toBe(
      "No speech detected. Please try again."
    );
    expect(result.current.isListening).toBe(false);
  });

  it("should handle missing microphone", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      getRecognition().onerror?.({ error: "audio-capture" });
    });

    expect(result.current.error).toBe("No microphone was found.");
  });

  it("should normalize technical terms in transcript", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      getRecognition().onresult?.({
        resultIndex: 0,
        results: {
          length: 2,
          0: {
            0: { transcript: "I use postgre sql" },
            isFinal: true,
          },
          1: {
            0: { transcript: "and next js" },
            isFinal: true,
          },
        },
      });
    });

    expect(result.current.transcript).toBe(
      "I use PostgreSQL and Next.js"
    );
  });

  it("should stop listening", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      result.current.startListening();
    });

    act(() => {
      result.current.stopListening();
    });

    expect(getRecognition().stop).toHaveBeenCalled();
    expect(result.current.isListening).toBe(false);
  });

  it("should clear transcript and error on reset", () => {
    const { result } = renderHook(() => useSpeechRecognition());

    act(() => {
      getRecognition().onerror?.({ error: "not-allowed" });
    });

    act(() => {
      result.current.resetTranscript();
    });

    expect(result.current.transcript).toBe("");
    expect(result.current.error).toBeNull();
  });
});

describe("normalizeTechnicalTerms", () => {
  it("should normalize supported technical vocabulary", () => {
    expect(
      normalizeTechnicalTerms(
        "fast api, super base, git hub, type script, gemini"
      )
    ).toBe("FastAPI, Supabase, GitHub, TypeScript, Gemini");
  });
});

describe("unsupported browser", () => {
  it("should not crash when SpeechRecognition is unavailable", () => {
    delete (window as Window & {
      SpeechRecognition?: unknown;
    }).SpeechRecognition;

    const { result } = renderHook(() => useSpeechRecognition());

    expect(result.current.isSupported).toBe(false);

    act(() => {
      result.current.startListening();
    });

    expect(result.current.isListening).toBe(false);
  });
});
