'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search } from 'lucide-react'
import { authFetch } from '@/lib/api'

interface Patient {
  id: string
  name: string
  email: string
  created_at: string
  total_visits?: number
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

const MOCK: Patient[] = [
  { id:'1', name:'Ahmed Khan',    email:'ahmed@example.com',   created_at: new Date().toISOString(), total_visits: 4  },
  { id:'2', name:'Sara Ali',      email:'sara@example.com',    created_at: new Date().toISOString(), total_visits: 2  },
  { id:'3', name:'Usman Tariq',   email:'usman@example.com',   created_at: new Date().toISOString(), total_visits: 7  },
  { id:'4', name:'Fatima Raza',   email:'fatima@example.com',  created_at: new Date().toISOString(), total_visits: 1  },
  { id:'5', name:'Bilal Hassan',  email:'bilal@example.com',   created_at: new Date().toISOString(), total_visits: 3  },
  { id:'6', name:'Nadia Malik',   email:'nadia@example.com',   created_at: new Date().toISOString(), total_visits: 6  },
]

export default function PatientsPage() {
  const router  = useRouter()
  const [patients, setPatients] = useState<Patient[]>(MOCK)
  const [search,   setSearch]   = useState('')
  const [ready,    setReady]    = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.push('/login'); return }
    setReady(true)
  }, [router])

  const fetchPatients = useCallback(async () => {
    try {
      const [pRes, aRes] = await Promise.allSettled([
        authFetch('/patients'),
        authFetch('/appointments'),
      ])

      let apptCounts: Record<string, number> = {}
      if (aRes.status === 'fulfilled' && aRes.value.ok) {
        const appts: { patient_id: string }[] = await aRes.value.json()
        appts.forEach(a => { apptCounts[a.patient_id] = (apptCounts[a.patient_id] ?? 0) + 1 })
      }

      if (pRes.status === 'fulfilled' && pRes.value.ok) {
        const list: Patient[] = await pRes.value.json()
        setPatients(list.map(p => ({ ...p, total_visits: apptCounts[p.id] ?? 0 })))
      }
    } catch { /* keep mock */ }
  }, [])

  useEffect(() => { if (ready) fetchPatients() }, [ready, fetchPatients])

  if (!ready) return null

  const filtered = patients.filter(p =>
    !search.trim() || p.name.toLowerCase().includes(search.toLowerCase()) || p.email.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Patients</h1>
        <p style={{ color: '#64748b', fontSize: '.8125rem', margin: '4px 0 0' }}>{patients.length} total patients</p>
      </div>

      <div style={{ background: '#fff', borderRadius: '16px', padding: '20px', boxShadow: '0 1px 8px rgba(0,0,0,.06)' }}>

        {/* Search */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text" placeholder="Search patients..." value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ padding: '7px 10px 7px 30px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '.8125rem', color: '#334155', outline: 'none', background: '#f8fafc', width: '220px' }}
            />
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '400px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                {['Patient','Email','Join Date','Total Visits'].map(h => (
                  <th key={h} style={{ padding: '6px 10px', fontSize: '.6875rem', fontWeight: 600, color: '#94a3b8', textAlign: 'left', whiteSpace: 'nowrap', textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid #f8fafc' }}>
                  <td style={{ padding: '12px 10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg,#e0e7ff,#c7d2fe)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.875rem', fontWeight: 700, color: '#4f46e5', flexShrink: 0 }}>
                        {p.name.charAt(0)}
                      </div>
                      <span style={{ fontSize: '.875rem', fontWeight: 600, color: '#1e293b' }}>{p.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 10px', fontSize: '.8125rem', color: '#64748b' }}>{p.email || '—'}</td>
                  <td style={{ padding: '12px 10px', fontSize: '.8125rem', color: '#64748b', whiteSpace: 'nowrap' }}>
                    {p.created_at ? fmtDate(p.created_at) : '—'}
                  </td>
                  <td style={{ padding: '12px 10px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', borderRadius: '50%', background: (p.total_visits ?? 0) > 0 ? 'rgba(59,130,246,.1)' : '#f1f5f9', color: (p.total_visits ?? 0) > 0 ? '#2563eb' : '#94a3b8', fontSize: '.8125rem', fontWeight: 700 }}>
                      {p.total_visits ?? 0}
                    </span>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={4} style={{ padding: '32px', textAlign: 'center', color: '#94a3b8', fontSize: '.875rem' }}>No patients found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
