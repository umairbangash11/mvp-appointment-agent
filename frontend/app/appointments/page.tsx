"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { clearTokens } from "@/lib/auth";
import { formatDate, formatStatus } from "@/lib/utils";
import AuthGuard from "@/components/auth-guard";
import InactivityLogout from "@/components/inactivity-logout";

interface Appointment {
  id: string;
  scheduled_at: string | null;
  status: string;
  booking_channel: string;
  patient_id: string;
  duration_minutes: number;
}

export default function AppointmentsPage() {
  return (
    <AuthGuard>
      <InactivityLogout />
      <AppointmentsContent />
    </AuthGuard>
  );
}

function AppointmentsContent() {
  const router = useRouter();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "scheduled" | "cancelled" | "completed">("all");

  useEffect(() => {
    api
      .get("/appointments")
      .then((res) => setAppointments(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleCancel(id: string) {
    if (!confirm("Cancel this appointment?")) return;
    setCancelling(id);
    try {
      await api.put(`/appointments/${id}/cancel`);
      setAppointments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: "cancelled" } : a))
      );
    } catch {
      alert("Failed to cancel. Please try again.");
    } finally {
      setCancelling(null);
    }
  }

  function logout() {
    clearTokens();
    router.push("/login");
  }

  const filtered = filter === "all" ? appointments : appointments.filter((a) => a.status === filter);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-bold">+</span>
          </div>
          <span className="font-semibold text-gray-900">Doctor Portal</span>
        </div>
        <div className="flex gap-4 items-center">
          <Link href="/dashboard" className="text-sm text-blue-600 hover:underline">Dashboard</Link>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-red-600 transition">
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">All Appointments</h1>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-6">
          {(["all", "scheduled", "completed", "cancelled"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-blue-400"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          <span className="ml-auto text-sm text-gray-400 self-center">{filtered.length} results</span>
        </div>

        {loading ? (
          <p className="text-gray-400 text-center py-12">Loading...</p>
        ) : filtered.length === 0 ? (
          <p className="text-gray-400 text-center py-12">No appointments found.</p>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
            {filtered.map((a) => (
              <AppointmentRow
                key={a.id}
                appointment={a}
                onCancel={handleCancel}
                cancelling={cancelling === a.id}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function AppointmentRow({
  appointment: a,
  onCancel,
  cancelling,
}: {
  appointment: Appointment;
  onCancel: (id: string) => void;
  cancelling: boolean;
}) {
  const statusColors: Record<string, string> = {
    scheduled: "text-green-700 bg-green-50",
    cancelled: "text-red-700 bg-red-50",
    completed: "text-gray-700 bg-gray-100",
  };

  return (
    <div className="px-6 py-4 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900">{formatDate(a.scheduled_at)}</p>
        <p className="text-xs text-gray-400 mt-0.5 capitalize">
          {a.booking_channel} · {a.duration_minutes} min · Patient ID: {a.patient_id.slice(0, 8)}...
        </p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusColors[a.status] || ""}`}>
          {formatStatus(a.status)}
        </span>
        {a.status === "scheduled" && (
          <button
            onClick={() => onCancel(a.id)}
            disabled={cancelling}
            className="text-xs text-red-600 hover:underline disabled:opacity-50"
          >
            {cancelling ? "Cancelling..." : "Cancel"}
          </button>
        )}
      </div>
    </div>
  );
}
