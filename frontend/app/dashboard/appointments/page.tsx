'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { XCircle, Search } from 'lucide-react'
import { authFetch } from '@/lib/api'

interface Appointment {
  id: string
  patient_name: string
  scheduled_at: string
  branch: string
  reason_for_visit: string
  status: string
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    scheduled: { bg: 'rgba(16,185,129,.12)',  color: '#059669', label: 'Confirmed' },
    pending:   { bg: 'rgba(245,158,11,.12)',  color: '#d97706', label: 'Pending'   },
    cancelled: { bg: 'rgba(239,68,68,.12)',   color: '#dc2626', label: 'Cancelled' },
    completed: { bg: 'rgba(99,102,241,.12)',  color: '#4f46e5', label: 'Completed' },
  }
  const s = map[status] ?? map.pending
  return (
    <span style={{ padding: '3px 10px', borderRadius: '20px', fontSize: '.6875rem', fontWeight: 600, background: s.bg, color: s.color, whiteSpace: 'nowrap' }}>
      {s.label}
    </span>
  )
}

const MOCK: Appointment[] = [
  { id:'1', patient_name:'Ahmed Khan',    scheduled_at: new Date().toISOString(), branch:'F10',    reason_for_visit:'Follow-up',    status:'scheduled' },
  { id:'2', patient_name:'Sara Ali',      scheduled_at: new Date().toISOString(), branch:'Bahria', reason_for_visit:'Consultation', status:'scheduled' },
  { id:'3', patient_name:'Fatima Raza',   scheduled_at: new Date().toISOString(), branch:'Bahria', reason_for_visit:'Vaccination',  status:'cancelled' },
  { id:'4', patient_name:'Bilal Hassan',  scheduled_at: new Date().toISOString(), branch:'F10',    reason_for_visit:'Blood test',   status:'completed' },
]

export default function AppointmentsPage() {
  const router = useRouter()
  const [appts,       setAppts]      = useState<Appointment[]>(MOCK)
  const [filter,      setFilter]     = useState<'all'|'scheduled'|'cancelled'|'completed'>('all')
  const [search,      setSearch]     = useState('')
  const [cancellingId, setCancelId] = useState<string | null>(null)
  const [ready,       setReady]      = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.push('/login'); return }
    setReady(true)
  }, [router])

  const fetchAppts = useCallback(async () => {
    const res = await authFetch('/appointments')
    if (res.ok) setAppts(await res.json())
  }, [])

  useEffect(() => { if (ready) fetchAppts() }, [ready, fetchAppts])

  const cancelAppt = async (id: string) => {
    setCancelId(id)
    try {
      const res = await authFetch(`/appointments/${id}/cancel`, { method: 'PUT' })
      if (res.ok) setAppts(prev => prev.map(a => a.id === id ? { ...a, status: 'cancelled' } : a))
    } finally { setCancelId(null) }
  }

  if (!ready) return null

  const filtered = appts.filter(a => {
    const matchStatus = filter === 'all' || a.status === filter
    const matchSearch = !search.trim() || a.patient_name.toLowerCase().includes(search.toLowerCase())
    return matchStatus && matchSearch
  })

  const counts = {
    all:       appts.length,
    scheduled: appts.filter(a => a.status === 'scheduled').length,
    cancelled: appts.filter(a => a.status === 'cancelled').length,
    completed: appts.filter(a => a.status === 'completed').length,
  }

  return (
    <>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Appointments</h1>
        <p style={{ color: '#64748b', fontSize: '.8125rem', margin: '4px 0 0' }}>All scheduled appointments</p>
      </div>

      <div style={{ background: '#fff', borderRadius: '16px', padding: '20px', boxShadow: '0 1px 8px rgba(0,0,0,.06)' }}>

        {/* Filter tabs + Search */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', gap: '4px', background: '#f1f5f9', borderRadius: '10px', padding: '3px' }}>
            {(['all', 'scheduled', 'cancelled', 'completed'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: '6px 12px', borderRadius: '7px', border: 'none', cursor: 'pointer',
                background: filter === f ? '#fff' : 'transparent',
                color: filter === f ? '#0f172a' : '#64748b',
                fontSize: '.75rem', fontWeight: filter === f ? 600 : 400,
                boxShadow: filter === f ? '0 1px 4px rgba(0,0,0,.08)' : 'none',
                transition: 'all .15s',
              }}>
                {f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
              </button>
            ))}
          </div>

          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text" placeholder="Search patient..." value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ padding: '7px 10px 7px 30px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '.8125rem', color: '#334155', outline: 'none', background: '#f8fafc', width: '200px' }}
            />
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '600px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                {['Patient Name','Date','Time','Branch','Reason','Status',''].map(h => (
                  <th key={h} style={{ padding: '6px 10px', fontSize: '.6875rem', fontWeight: 600, color: '#94a3b8', textAlign: 'left', whiteSpace: 'nowrap', textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(appt => (
                <tr key={appt.id} style={{ borderBottom: '1px solid #f8fafc' }}>
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'linear-gradient(135deg,#e0e7ff,#c7d2fe)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.75rem', fontWeight: 700, color: '#4f46e5', flexShrink: 0 }}>
                        {appt.patient_name.charAt(0)}
                      </div>
                      <span style={{ fontSize: '.8125rem', fontWeight: 500, color: '#1e293b', whiteSpace: 'nowrap' }}>{appt.patient_name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '10px', fontSize: '.8125rem', color: '#64748b', whiteSpace: 'nowrap' }}>{fmtDate(appt.scheduled_at)}</td>
                  <td style={{ padding: '10px', fontSize: '.8125rem', color: '#64748b', whiteSpace: 'nowrap' }}>{fmtTime(appt.scheduled_at)}</td>
                  <td style={{ padding: '10px' }}>
                    <span style={{ fontSize: '.6875rem', fontWeight: 600, padding: '3px 8px', borderRadius: '6px', whiteSpace: 'nowrap',
                      background: appt.branch === 'F10' ? 'rgba(59,130,246,.1)' : 'rgba(16,185,129,.1)',
                      color:      appt.branch === 'F10' ? '#2563eb'             : '#059669' }}>
                      {appt.branch || '—'}
                    </span>
                  </td>
                  <td style={{ padding: '10px', fontSize: '.8125rem', color: '#64748b' }}>{appt.reason_for_visit}</td>
                  <td style={{ padding: '10px' }}><StatusBadge status={appt.status} /></td>
                  <td style={{ padding: '10px' }}>
                    {appt.status !== 'cancelled' && appt.status !== 'completed' && (
                      <button onClick={() => cancelAppt(appt.id)} disabled={cancellingId === appt.id}
                        title="Cancel" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', opacity: cancellingId === appt.id ? .4 : .6, padding: '2px', display: 'flex' }}>
                        <XCircle size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#94a3b8', fontSize: '.875rem' }}>No appointments found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
