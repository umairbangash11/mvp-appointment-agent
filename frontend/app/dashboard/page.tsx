"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { formatDate, formatStatus } from "@/lib/utils";
import AuthGuard from "@/components/auth-guard";
import InactivityLogout from "@/components/inactivity-logout";
import Navbar from "@/components/navbar";

interface Appointment {
  id: string;
  scheduled_at: string | null;
  status: string;
  booking_channel: string;
  patient_name: string;
  reason_for_visit: string;
  branch: string;
}

interface Stats {
  today_appointments: number;
  total_appointments: number;
  total_patients: number;
  upcoming_appointments: number;
  recent_appointments: Appointment[];
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
  const [stats, setStats]     = useState<Stats | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/auth/profile"), api.get("/appointments/stats")])
      .then(([p, s]) => { setProfile(p.data); setStats(s.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar doctorName={profile?.name} clinicName={profile?.clinic_name} />

      <main className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {/* 4 Stats cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="Today" value={stats?.today_appointments ?? 0} color="blue"   icon="📅" />
          <StatCard label="Upcoming" value={stats?.upcoming_appointments ?? 0} color="orange" icon="⏰" />
          <StatCard label="Total Appts" value={stats?.total_appointments ?? 0} color="green"  icon="📋" />
          <StatCard label="Patients" value={stats?.total_patients ?? 0} color="purple" icon="👤" />
        </div>

        {/* Recent appointments */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Appointments</h2>
            <Link href="/appointments" className="text-sm text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          {!stats?.recent_appointments?.length ? (
            <p className="text-gray-400 text-sm px-6 py-10 text-center">No appointments yet.</p>
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

function StatCard({
  label, value, color, icon,
}: {
  label: string; value: number; color: string; icon: string;
}) {
  const colors: Record<string, string> = {
    blue:   "bg-blue-50   text-blue-700   border-blue-100",
    orange: "bg-orange-50 text-orange-700 border-orange-100",
    green:  "bg-green-50  text-green-700  border-green-100",
    purple: "bg-purple-50 text-purple-700 border-purple-100",
  };
  return (
    <div className={`rounded-xl p-5 border ${colors[color]}`}>
      <div className="text-2xl mb-1">{icon}</div>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-xs mt-1 opacity-70">{label}</p>
    </div>
  );
}

function AppointmentRow({ appointment: a }: { appointment: Appointment }) {
  const statusColors: Record<string, string> = {
    scheduled: "text-green-700 bg-green-50",
    cancelled: "text-red-700   bg-red-50",
    completed: "text-gray-700  bg-gray-100",
  };
  return (
    <div className="px-6 py-4 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900">
          {a.patient_name || "Unknown Patient"}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          {formatDate(a.scheduled_at)}
          {a.branch ? ` · ${a.branch}` : ""}
        </p>
        {a.reason_for_visit && (
          <p className="text-xs text-gray-400 mt-0.5 truncate max-w-sm">
            {a.reason_for_visit}
          </p>
        )}
      </div>
      <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium flex-shrink-0 ${statusColors[a.status] || ""}`}>
        {formatStatus(a.status)}
      </span>
    </div>
  );
}
