export type AssistantVoiceCommand = "leaderboard" | "goal" | null;

/**
 * Detects whether an incoming assistant query or voice transcript is a recognized
 * navigation or status command.
 *
 * Supported commands:
 * - "leaderboard": Questions asking for the student's leaderboard rank or standing.
 * - "goal": Questions asking whether student goals were achieved or requesting goal status.
 *
 * Returns:
 * - "leaderboard" | "goal" if a command is recognized.
 * - null for general academic questions and regular chat messages.
 */
export function detectAssistantVoiceCommand(query: string): AssistantVoiceCommand {
  if (!query || typeof query !== "string") {
    return null;
  }

  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  // 1. Leaderboard Rank Voice Commands
  const isLeaderboardQuery =
    /\b(leaderboard\s+rank|my\s+rank|show.*rank|what.*rank|tell\s+me.*rank)\b/i.test(normalized) ||
    (normalized.includes("leaderboard") &&
      (normalized.includes("rank") ||
        normalized.includes("standing") ||
        normalized.includes("position") ||
        normalized.includes("show")));

  if (isLeaderboardQuery) {
    return "leaderboard";
  }

  // 2. Goal Achievement & Status Voice Commands
  const isGoalQuery =
    /\b(achieve|achieved|status|progress|complete|completed)\b.*\bgoal\b/i.test(normalized) ||
    /\bgoal\b.*\b(achieve|achieved|status|progress|reached)\b/i.test(normalized) ||
    /\b(did\s+i|have\s+i)\s+achieve/i.test(normalized) ||
    normalized.includes("show my goal") ||
    normalized.includes("my goal status");

  if (isGoalQuery) {
    return "goal";
  }

  return null;
}

