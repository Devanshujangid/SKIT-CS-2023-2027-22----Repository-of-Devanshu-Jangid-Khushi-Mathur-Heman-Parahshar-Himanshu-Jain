"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function OnboardingPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    semester: "",
    study_hours_per_day: "",
    goals: "",
    subjects: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const token = await getToken();

      const payload = {
        semester: parseInt(formData.semester),
        study_hours_per_day: parseFloat(formData.study_hours_per_day),
        goals: formData.goals,
        subjects: formData.subjects.split(",").map((s) => s.trim()).filter(Boolean),
      };

      const response = await fetch("http://localhost:8000/api/v1/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Failed to create profile");
      }

      router.push("/dashboard");
    } catch (error) {
      console.error("Error submitting profile:", error);
      alert("Failed to save profile. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-md">
        <h1 className="mb-6 text-2xl font-bold text-slate-900">Complete Your Profile</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Semester</label>
            <input
              type="number"
              name="semester"
              required
              value={formData.semester}
              onChange={handleChange}
              className="w-full rounded-md border p-2 text-slate-900"
              placeholder="e.g., 5"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Daily Study Hours</label>
            <input
              type="number"
              step="0.5"
              name="study_hours_per_day"
              required
              value={formData.study_hours_per_day}
              onChange={handleChange}
              className="w-full rounded-md border p-2 text-slate-900"
              placeholder="e.g., 4.5"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Learning Goals</label>
            <textarea
              name="goals"
              required
              value={formData.goals}
              onChange={handleChange}
              className="w-full rounded-md border p-2 text-slate-900"
              placeholder="Score 9.0 CGPA and master backend architecture"
              rows={3}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Subjects (comma-separated)</label>
            <input
              type="text"
              name="subjects"
              required
              value={formData.subjects}
              onChange={handleChange}
              className="w-full rounded-md border p-2 text-slate-900"
              placeholder="Operating Systems, Computer Networks"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-4 w-full rounded-md bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? "Saving..." : "Save Profile"}
          </button>
        </form>
      </div>
    </main>
  );
}