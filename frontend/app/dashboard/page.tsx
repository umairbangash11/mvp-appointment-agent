"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { clearTokens } from "@/lib/auth";
import { formatDate, formatStatus } from "@/lib/utils";
import AuthGuard from "@/components/auth-guard";
import InactivityLogout from "@/components/inactivity-logout";

interface Stats {
  today_appointments: number;
  total_appointments: number;
  total_patients: number;
  recent_appointments: Appointment[];
}

interface Appointment {
  id: string;
  scheduled_at: string | null;
  status: string;
  booking_channel: string;
  patient_id: string;
}

interface Profile {
  name: string;
  clinic_name: string;
  email: string;
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <InactivityLogout />
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/auth/profile"),
      api.get("/appointments/stats"),
    ])
      .then(([profileRes, statsRes]) => {
        setProfile(profileRes.data);
        setStats(statsRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function logout() {
    clearTokens();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-bold">+</span>
          </div>
          <div>
            <p className="font-semibold text-gray-900">{profile?.name || "Doctor"}</p>
            <p className="text-xs text-gray-500">{profile?.clinic_name}</p>
          </div>
        </div>
        <div className="flex gap-4 items-center">
          <Link href="/appointments" className="text-sm text-blue-600 hover:underline">
            All Appointments
          </Link>
          <Link href="/whatsapp-test" className="text-sm text-green-600 hover:underline">
            WhatsApp Simulator
          </Link>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-red-600 transition"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {/* Stats cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatCard label="Today's Appointments" value={stats?.today_appointments ?? 0} color="blue" />
          <StatCard label="Total Appointments" value={stats?.total_appointments ?? 0} color="green" />
          <StatCard label="Total Patients" value={stats?.total_patients ?? 0} color="purple" />
        </div>

        {/* Recent appointments */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Appointments</h2>
            <Link href="/appointments" className="text-sm text-blue-600 hover:underline">
              View all
            </Link>
          </div>
          {!stats?.recent_appointments?.length ? (
            <p className="text-gray-400 text-sm px-6 py-8 text-center">No appointments yet.</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {stats.recent_appointments.map((a) => (
                <AppointmentRow key={a.id} appointment={a} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    purple: "bg-purple-50 text-purple-700",
  };
  return (
    <div className={`rounded-xl p-5 ${colors[color]}`}>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-sm mt-1 opacity-80">{label}</p>
    </div>
  );
}

function AppointmentRow({ appointment: a }: { appointment: Appointment }) {
  const statusColors: Record<string, string> = {
    scheduled: "text-green-700 bg-green-50",
    cancelled: "text-red-700 bg-red-50",
    completed: "text-gray-700 bg-gray-100",
  };
  return (
    <div className="px-6 py-3 flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-900 font-medium">{formatDate(a.scheduled_at)}</p>
        <p className="text-xs text-gray-400 capitalize">{a.booking_channel} booking</p>
      </div>
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[a.status] || ""}`}>
        {formatStatus(a.status)}
      </span>
    </div>
  );
}
