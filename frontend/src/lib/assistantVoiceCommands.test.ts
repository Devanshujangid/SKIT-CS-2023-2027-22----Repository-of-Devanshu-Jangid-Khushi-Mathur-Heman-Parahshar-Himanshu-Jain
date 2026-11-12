import { describe, expect, it } from "vitest";
import { detectAssistantVoiceCommand } from "./assistantVoiceCommands";

describe("detectAssistantVoiceCommand", () => {
  describe("Leaderboard commands", () => {
    it("detects show my leaderboard rank", () => {
      expect(
        detectAssistantVoiceCommand("Show my leaderboard rank")
      ).toBe("leaderboard");
    });

    it("detects leaderboard rank questions", () => {
      expect(
        detectAssistantVoiceCommand("What is my leaderboard rank?")
      ).toBe("leaderboard");
    });

    it("detects tell me my rank", () => {
      expect(
        detectAssistantVoiceCommand("Tell me my rank")
      ).toBe("leaderboard");
    });
  });

  describe("Goal commands", () => {
    it("detects goal achievement questions", () => {
      expect(
        detectAssistantVoiceCommand("Did I achieve my goal?")
      ).toBe("goal");
    });

    it("detects goal completion questions", () => {
      expect(
        detectAssistantVoiceCommand("Have I achieved my goal?")
      ).toBe("goal");
    });

    it("detects goal status requests", () => {
      expect(
        detectAssistantVoiceCommand("Show my goal status")
      ).toBe("goal");
    });
  });

  describe("Normal academic questions", () => {
    it("does not classify normal questions as commands", () => {
      expect(
        detectAssistantVoiceCommand("Explain deadlock prevention")
      ).toBeNull();
    });

    it("handles empty input", () => {
      expect(detectAssistantVoiceCommand("")).toBeNull();
    });
  });
});