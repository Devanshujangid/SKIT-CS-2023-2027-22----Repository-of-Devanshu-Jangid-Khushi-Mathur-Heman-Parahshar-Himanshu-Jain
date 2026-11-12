// Supabase Edge Function: Daily Automated Notification Engine Dispatch
// Runs daily via Supabase Scheduled Triggers / cron to push alerts for:
// - "Upcoming Exams"
// - "Unresolved Weak Topics"

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.");
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Call stored procedure to dispatch daily alerts with idempotency
    const { data, error } = await supabase.rpc(
      "dispatch_daily_exam_and_weak_topic_alerts"
    );

    if (error) {
      console.error("Error executing dispatch_daily_exam_and_weak_topic_alerts:", error);
      throw error;
    }

    const count = Array.isArray(data) ? data.length : 0;
    console.log(`Daily notification engine completed successfully. Pushed ${count} alerts.`);

    return new Response(
      JSON.stringify({
        success: true,
        message: `Successfully executed daily notification engine. Dispatched ${count} alerts.`,
        dispatched_count: count,
        alerts: data,
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 200,
      }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return new Response(
      JSON.stringify({ success: false, error: message }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      }
    );
  }
});

