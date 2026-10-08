"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Show } from "@clerk/nextjs";
import { Sparkles, BrainCircuit, LineChart, CalendarRange, ArrowRight, Zap, Target } from "lucide-react";

export default function HomePage() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  if (!isMounted) return null;

  return (
    <main className="relative flex flex-col items-center min-h-screen overflow-hidden bg-[#FAFAFA] selection:bg-indigo-200 selection:text-indigo-900">
      
      {/* Awwwards Style Ambient Blur Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-300/30 mix-blend-multiply filter blur-[100px] animate-pulse pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] w-[400px] h-[400px] rounded-full bg-purple-300/30 mix-blend-multiply filter blur-[100px] animate-pulse delay-700 pointer-events-none" />
      
      {/* Super Fine Engineering Grid */}
      <div className="absolute inset-0 z-0 h-full w-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Dynamic Cursor Spotlight */}
      <div
        className="pointer-events-none fixed inset-0 z-50 transition-opacity duration-300"
        style={{
          background: `radial-gradient(400px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(99, 102, 241, 0.04), transparent 80%)`,
        }}
      />

      <div className="relative z-10 w-full max-w-7xl px-6 pt-32 pb-20 sm:pt-48 sm:px-12">
        
        {/* Floating Glassmorphic Badge */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold tracking-wide text-slate-800 uppercase transition-all duration-500 border rounded-full bg-white/40 backdrop-blur-md border-white/60 shadow-[0_4px_24px_-8px_rgba(0,0,0,0.1)] hover:shadow-[0_4px_24px_-8px_rgba(99,102,241,0.3)] hover:bg-white/60 cursor-default">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Gemini 3.6 Flash Engine</span>
          </div>
        </div>

        {/* Hero Headline (Tight tracking, high contrast) */}
        <h1 className="max-w-5xl mx-auto text-6xl font-black tracking-tighter text-center sm:text-8xl text-slate-900 leading-[1.05]">
          Intelligence meets <br className="hidden sm:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-br from-indigo-600 via-purple-600 to-indigo-800">
            discipline.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="max-w-2xl mx-auto mt-8 text-lg font-medium leading-relaxed text-center text-slate-500 sm:text-xl">
          Drop your syllabus. Set your CGPA target. Let our deterministic AI engine architect the perfect 7-day academic master plan.
        </p>

        {/* Call to Actions */}
        <div className="flex flex-col items-center justify-center gap-5 mt-12 sm:flex-row">
          <Show when="signed-out">
            <Link href="/sign-up" className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-white transition-all duration-300 bg-slate-900 rounded-2xl hover:bg-slate-800 hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:-translate-y-0.5 overflow-hidden">
              <span className="relative z-10 flex items-center gap-2">
                Start Planning <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
            <Link href="/sign-in" className="inline-flex items-center justify-center px-8 py-4 text-base font-bold transition-all duration-300 bg-white/50 border border-slate-200/60 backdrop-blur-sm rounded-2xl text-slate-700 hover:bg-white hover:shadow-sm hover:-translate-y-0.5">
              Sign In
            </Link>
          </Show>
          <Show when="signed-in">
            <Link href="/dashboard" className="group relative inline-flex items-center justify-center px-8 py-4 text-base font-bold text-white transition-all duration-300 bg-indigo-600 rounded-2xl hover:bg-indigo-700 hover:shadow-[0_8px_30px_rgba(79,70,229,0.3)] hover:-translate-y-0.5 overflow-hidden">
              <span className="relative z-10 flex items-center gap-2">
                Enter Dashboard <Zap className="w-4 h-4 transition-transform group-hover:scale-110" />
              </span>
            </Link>
          </Show>
        </div>
      </div>

      {/* Asymmetric Bento Grid Features */}
      <div className="relative z-10 w-full max-w-7xl px-6 pb-32 mx-auto sm:px-12">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 md:grid-rows-2">
          
          {/* Large Feature Card (Spans 2 columns) */}
          <div className="flex flex-col justify-between p-10 transition-all duration-500 bg-white border md:col-span-2 rounded-[2rem] border-slate-200/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] group overflow-hidden relative">
            <div className="absolute top-0 right-0 w-64 h-64 transition-transform duration-700 translate-x-16 -translate-y-16 rounded-full bg-gradient-to-br from-indigo-50 to-purple-50 group-hover:scale-110 -z-10" />
            <div>
              <div className="flex items-center justify-center w-14 h-14 mb-8 bg-indigo-100 rounded-2xl text-indigo-600 group-hover:scale-110 transition-transform duration-500">
                <BrainCircuit className="w-7 h-7" />
              </div>
              <h3 className="mb-4 text-3xl font-black tracking-tight text-slate-900">Deterministic AI Modeling</h3>
              <p className="max-w-md text-base leading-relaxed text-slate-500">
                Gemini 3.6 Flash calculates strict daily hour limits, applying complex difficulty weights to your enrolled subjects to guarantee an executable, balanced week without burnout.
              </p>
            </div>
          </div>

          {/* Square Card 1 */}
          <div className="flex flex-col justify-between p-10 transition-all duration-500 bg-white border rounded-[2rem] border-slate-200/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] group">
            <div className="flex items-center justify-center w-14 h-14 mb-8 bg-emerald-100 rounded-2xl text-emerald-600 group-hover:scale-110 transition-transform duration-500">
              <CalendarRange className="w-7 h-7" />
            </div>
            <div>
              <h3 className="mb-3 text-xl font-bold text-slate-900">Native Exports</h3>
              <p className="text-sm leading-relaxed text-slate-500">
                Instantly generate zero-dependency PDF printouts or download raw `.ics` blobs directly to your Apple or Google Calendar.
              </p>
            </div>
          </div>

          {/* Square Card 2 */}
          <div className="flex flex-col justify-between p-10 transition-all duration-500 bg-white border rounded-[2rem] border-slate-200/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] group">
            <div className="flex items-center justify-center w-14 h-14 mb-8 bg-purple-100 rounded-2xl text-purple-600 group-hover:scale-110 transition-transform duration-500">
              <Target className="w-7 h-7" />
            </div>
            <div>
              <h3 className="mb-3 text-xl font-bold text-slate-900">Goal Alignment</h3>
              <p className="text-sm leading-relaxed text-slate-500">
                Every task generated is mathematically aligned with your target CGPA, ensuring your primary focus stays locked in.
              </p>
            </div>
          </div>

          {/* Wide Card (Spans 2 columns on bottom) */}
          <div className="flex flex-col justify-between p-10 transition-all duration-500 bg-slate-900 border md:col-span-2 rounded-[2rem] border-slate-800 shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgba(99,102,241,0.2)] group relative overflow-hidden">
            <div className="absolute top-0 right-0 w-full h-full bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.15),transparent_50%)] pointer-events-none" />
            <div>
              <div className="flex items-center justify-center w-14 h-14 mb-8 bg-white/10 rounded-2xl text-white group-hover:scale-110 transition-transform duration-500">
                <LineChart className="w-7 h-7" />
              </div>
              <h3 className="mb-4 text-3xl font-black tracking-tight text-white">Stateful Persistence</h3>
              <p className="max-w-md text-base leading-relaxed text-slate-400">
                Check off daily milestones with interactive UI logic. Your progress is securely persisted across browser sessions locally, ensuring you never lose track of your week.
              </p>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}