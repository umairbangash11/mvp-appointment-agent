'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { TrendingUp, UserCheck, Calendar, CalendarCheck, XCircle } from 'lucide-react'
import { authFetch } from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Appointment {
  id: string
  patient_name: string
  scheduled_at: string
  branch: string
  reason_for_visit: string
  status: string
}

interface Stats {
  today_appointments: number
  upcoming_appointments: number
  total_patients: number
  total_appointments: number
}

interface DoctorProfile { name: string; clinic_name: string }

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })

// ── Mock data ─────────────────────────────────────────────────────────────────

const now = new Date()
const d = (h: number, m: number) => { const t = new Date(now); t.setHours(h, m, 0, 0); return t.toISOString() }

const MOCK_STATS: Stats = { today_appointments: 8, upcoming_appointments: 34, total_patients: 247, total_appointments: 112 }

const MOCK_APPTS: Appointment[] = [
  { id:'1', patient_name:'Ahmed Khan',    scheduled_at: d(9,0),  branch:'F10',    reason_for_visit:'Follow-up',    status:'scheduled'  },
  { id:'2', patient_name:'Sara Ali',      scheduled_at: d(10,30),branch:'Bahria', reason_for_visit:'Consultation', status:'scheduled'  },
  { id:'3', patient_name:'Usman Tariq',   scheduled_at: d(11,0), branch:'F10',    reason_for_visit:'Check-up',     status:'scheduled'  },
  { id:'4', patient_name:'Fatima Raza',   scheduled_at: d(12,30),branch:'Bahria', reason_for_visit:'Vaccination',  status:'cancelled'  },
  { id:'5', patient_name:'Bilal Hassan',  scheduled_at: d(14,0), branch:'F10',    reason_for_visit:'Blood test',   status:'scheduled'  },
  { id:'6', patient_name:'Nadia Malik',   scheduled_at: d(15,30),branch:'Bahria', reason_for_visit:'Prescription', status:'scheduled'  },
  { id:'7', patient_name:'Zara Chaudhry', scheduled_at: d(16,0), branch:'F10',    reason_for_visit:'X-ray review', status:'scheduled'  },
]

const WEEKLY = [
  { day:'Mon', f10:6, bahria:4 }, { day:'Tue', f10:8, bahria:5 },
  { day:'Wed', f10:5, bahria:7 }, { day:'Thu', f10:9, bahria:6 },
  { day:'Fri', f10:7, bahria:8 }, { day:'Sat', f10:4, bahria:3 },
]

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg:string; color:string; label:string }> = {
    scheduled:  { bg:'rgba(16,185,129,.12)',  color:'#059669', label:'Confirmed'  },
    pending:    { bg:'rgba(245,158,11,.12)',  color:'#d97706', label:'Pending'    },
    cancelled:  { bg:'rgba(239,68,68,.12)',   color:'#dc2626', label:'Cancelled'  },
    completed:  { bg:'rgba(99,102,241,.12)',  color:'#4f46e5', label:'Completed'  },
  }
  const s = map[status] ?? map.pending
  return (
    <span style={{ padding:'3px 10px', borderRadius:'20px', fontSize:'.6875rem', fontWeight:600, background:s.bg, color:s.color, whiteSpace:'nowrap' }}>
      {s.label}
    </span>
  )
}

// ── Bar chart ─────────────────────────────────────────────────────────────────

function BarChart({ data }: { data: typeof WEEKLY }) {
  const max = Math.max(...data.flatMap(d => [d.f10, d.bahria])) + 2
  const W=560, H=180, padL=32, padB=30, padT=12
  const chartW = W - padL - 16, chartH = H - padB - padT
  const groupW = chartW / data.length, barW = groupW * 0.28
  const ySteps = [0, Math.round(max/3), Math.round(max*2/3), max]
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
      {ySteps.map(v => { const y = padT + chartH - (v/max)*chartH; return (
        <g key={v}>
          <line x1={padL} y1={y} x2={W-16} y2={y} stroke="rgba(0,0,0,.06)" strokeWidth="1"/>
          <text x={padL-6} y={y+4} fontSize="10" fill="#94a3b8" textAnchor="end">{v}</text>
        </g>
      )})}
      {data.map((d,i) => {
        const cx = padL + i*groupW + groupW/2
        const f10H=(d.f10/max)*chartH, bahH=(d.bahria/max)*chartH
        return (
          <g key={d.day}>
            <rect x={cx-barW-2} y={padT+chartH-f10H} width={barW} height={f10H} fill="#3b82f6" rx="3"/>
            <rect x={cx+2}      y={padT+chartH-bahH} width={barW} height={bahH}  fill="#10b981" rx="3"/>
            <text x={cx} y={H-8} fontSize="11" fill="#64748b" textAnchor="middle">{d.day}</text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Mini calendar ─────────────────────────────────────────────────────────────

const MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']
const DOW=['Su','Mo','Tu','We','Th','Fr','Sa']

function MiniCalendar({ appointmentDates }: { appointmentDates: string[] }) {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth())
  const [year,  setYear]  = useState(now.getFullYear())
  const firstDow    = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month+1, 0).getDate()
  const cells = [...Array(firstDow).fill(null), ...Array.from({length:daysInMonth},(_,i)=>i+1)]
  const apptDays = new Set(appointmentDates.map(d => {
    const dt = new Date(d)
    return dt.getMonth()===month && dt.getFullYear()===year ? dt.getDate() : null
  }).filter(Boolean) as number[])
  return (
    <div>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'12px'}}>
        <button onClick={()=>month===0?(setMonth(11),setYear(y=>y-1)):setMonth(m=>m-1)} style={{background:'none',border:'none',cursor:'pointer',color:'#64748b',fontSize:'1.1rem',padding:'2px 6px',lineHeight:1}}>‹</button>
        <span style={{fontWeight:600,fontSize:'.875rem',color:'#1e293b'}}>{MONTHS[month]} {year}</span>
        <button onClick={()=>month===11?(setMonth(0),setYear(y=>y+1)):setMonth(m=>m+1)} style={{background:'none',border:'none',cursor:'pointer',color:'#64748b',fontSize:'1.1rem',padding:'2px 6px',lineHeight:1}}>›</button>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(7,1fr)',gap:'1px',marginBottom:'4px'}}>
        {DOW.map(d=><div key={d} style={{textAlign:'center',fontSize:'.625rem',fontWeight:600,color:'#94a3b8',padding:'2px 0'}}>{d}</div>)}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(7,1fr)',gap:'1px'}}>
        {cells.map((day,i)=>{
          if(!day) return <div key={`e-${i}`}/>
          const isToday=day===now.getDate()&&month===now.getMonth()&&year===now.getFullYear()
          const hasAppt=apptDays.has(day)
          return (
            <div key={`d-${day}`} style={{position:'relative',textAlign:'center',padding:'5px 1px',borderRadius:'6px',fontSize:'.75rem',cursor:'default',fontWeight:isToday?700:400,background:isToday?'#3b82f6':'transparent',color:isToday?'#fff':'#334155'}}>
              {day}
              {hasAppt&&!isToday&&<div style={{position:'absolute',bottom:'2px',left:'50%',transform:'translateX(-50%)',width:'4px',height:'4px',borderRadius:'50%',background:'#f59e0b'}}/>}
            </div>
          )
        })}
      </div>
      <div style={{marginTop:'14px',paddingTop:'12px',borderTop:'1px solid #f1f5f9',display:'flex',flexDirection:'column',gap:'6px'}}>
        <div style={{display:'flex',alignItems:'center',gap:'6px',fontSize:'.6875rem',color:'#64748b'}}>
          <div style={{width:'8px',height:'8px',borderRadius:'50%',background:'#3b82f6'}}/> Today
        </div>
        <div style={{display:'flex',alignItems:'center',gap:'6px',fontSize:'.6875rem',color:'#64748b'}}>
          <div style={{width:'5px',height:'5px',borderRadius:'50%',background:'#f59e0b'}}/> Has appointments
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter()
  const [stats,        setStats]       = useState<Stats>(MOCK_STATS)
  const [appts,        setAppts]       = useState<Appointment[]>(MOCK_APPTS)
  const [doctor,       setDoctor]      = useState<DoctorProfile>({ name: '', clinic_name: '' })
  const [cancellingId, setCancelId]    = useState<string|null>(null)
  const [ready,        setReady]       = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { router.push('/login'); return }
    setReady(true)
  }, [router])

  const fetchData = useCallback(async () => {
    const [sRes, aRes, pRes] = await Promise.allSettled([
      authFetch('/appointments/stats'),
      authFetch('/appointments'),
      authFetch('/auth/profile'),
    ])
    if (sRes.status==='fulfilled' && sRes.value.ok) setStats(await sRes.value.json())
    if (aRes.status==='fulfilled' && aRes.value.ok) {
      const all: Appointment[] = await aRes.value.json()
      const todayStr = new Date().toDateString()
      setAppts(all.filter(a => new Date(a.scheduled_at).toDateString() === todayStr))
    }
    if (pRes.status==='fulfilled' && pRes.value.ok) setDoctor(await pRes.value.json())
  }, [])

  useEffect(() => { if (ready) fetchData() }, [ready, fetchData])

  const cancelAppt = async (id: string) => {
    setCancelId(id)
    try {
      const res = await authFetch(`/appointments/${id}/cancel`, { method: 'PUT' })
      if (res.ok) setAppts(prev => prev.map(a => a.id===id ? {...a, status:'cancelled'} : a))
    } finally { setCancelId(null) }
  }

  if (!ready) return null

  const statCards = [
    { label:"Today's Appts",  value:stats.today_appointments,  gradient:'linear-gradient(135deg,#667eea,#764ba2)', Icon:CalendarCheck },
    { label:'Upcoming',       value:stats.upcoming_appointments,gradient:'linear-gradient(135deg,#11998e,#38ef7d)', Icon:TrendingUp    },
    { label:'Total Patients', value:stats.total_patients,       gradient:'linear-gradient(135deg,#f093fb,#f5576c)', Icon:UserCheck     },
    { label:'Total Appts',    value:stats.total_appointments,   gradient:'linear-gradient(135deg,#4facfe,#00f2fe)', Icon:Calendar      },
  ]

  return (
    <>
      {/* Header */}
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:'26px'}}>
        <div>
          <h1 style={{fontSize:'1.375rem',fontWeight:700,color:'#0f172a',margin:0}}>Good morning, {doctor.name || 'Doctor'} 👋</h1>
          <p style={{color:'#64748b',fontSize:'.8125rem',margin:'4px 0 0'}}>
            {new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}
          </p>
        </div>
        <div style={{width:'38px',height:'38px',borderRadius:'50%',background:'linear-gradient(135deg,#3b82f6,#8b5cf6)',display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontWeight:700,fontSize:'1rem',flexShrink:0}}>{doctor.name.charAt(0).toUpperCase() || 'D'}</div>
      </div>

      {/* Stats */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:'16px',marginBottom:'22px'}}>
        {statCards.map(({label,value,gradient,Icon})=>(
          <div key={label} style={{borderRadius:'16px',padding:'18px 20px',background:gradient,color:'#fff',position:'relative',overflow:'hidden',boxShadow:'0 4px 20px rgba(0,0,0,.1)'}}>
            <div style={{position:'absolute',right:'-8px',top:'-8px',opacity:.15}}><Icon size={74}/></div>
            <div style={{fontSize:'.6875rem',fontWeight:500,opacity:.88,marginBottom:'8px',textTransform:'uppercase',letterSpacing:'.04em'}}>{label}</div>
            <div style={{fontSize:'2.125rem',fontWeight:800,lineHeight:1}}>{value}</div>
          </div>
        ))}
      </div>

      {/* Table + Calendar */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 268px',gap:'18px',marginBottom:'18px',alignItems:'start'}}>

        {/* Patient table */}
        <div style={{background:'#fff',borderRadius:'16px',padding:'20px',boxShadow:'0 1px 8px rgba(0,0,0,.06)'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'14px'}}>
            <h2 style={{fontSize:'.9375rem',fontWeight:700,color:'#0f172a',margin:0}}>{"Today's Patients"}</h2>
            <span style={{fontSize:'.6875rem',color:'#64748b',background:'#f1f5f9',padding:'4px 10px',borderRadius:'20px',fontWeight:500}}>
              {appts.filter(a=>a.status!=='cancelled').length} active
            </span>
          </div>
          <div style={{overflowX:'auto'}}>
            <table style={{width:'100%',borderCollapse:'collapse',minWidth:'480px'}}>
              <thead>
                <tr style={{borderBottom:'1px solid #f1f5f9'}}>
                  {['Patient Name','Time','Branch','Reason','Status',''].map(h=>(
                    <th key={h} style={{padding:'6px 10px',fontSize:'.6875rem',fontWeight:600,color:'#94a3b8',textAlign:'left',whiteSpace:'nowrap',textTransform:'uppercase',letterSpacing:'.04em'}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {appts.map(appt=>(
                  <tr key={appt.id} style={{borderBottom:'1px solid #f8fafc'}}>
                    <td style={{padding:'10px'}}>
                      <div style={{display:'flex',alignItems:'center',gap:'8px'}}>
                        <div style={{width:'30px',height:'30px',borderRadius:'50%',background:'linear-gradient(135deg,#e0e7ff,#c7d2fe)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'.75rem',fontWeight:700,color:'#4f46e5',flexShrink:0}}>
                          {appt.patient_name.charAt(0)}
                        </div>
                        <span style={{fontSize:'.8125rem',fontWeight:500,color:'#1e293b',whiteSpace:'nowrap'}}>{appt.patient_name}</span>
                      </div>
                    </td>
                    <td style={{padding:'10px',fontSize:'.8125rem',color:'#64748b',whiteSpace:'nowrap'}}>{fmtTime(appt.scheduled_at)}</td>
                    <td style={{padding:'10px'}}>
                      <span style={{fontSize:'.6875rem',fontWeight:600,padding:'3px 8px',borderRadius:'6px',whiteSpace:'nowrap',
                        background:appt.branch==='F10'?'rgba(59,130,246,.1)':'rgba(16,185,129,.1)',
                        color:appt.branch==='F10'?'#2563eb':'#059669'}}>
                        {appt.branch || '—'}
                      </span>
                    </td>
                    <td style={{padding:'10px',fontSize:'.8125rem',color:'#64748b'}}>{appt.reason_for_visit}</td>
                    <td style={{padding:'10px'}}><StatusBadge status={appt.status}/></td>
                    <td style={{padding:'10px'}}>
                      {appt.status!=='cancelled'&&appt.status!=='completed'&&(
                        <button onClick={()=>cancelAppt(appt.id)} disabled={cancellingId===appt.id}
                          title="Cancel" style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',opacity:cancellingId===appt.id?.4:.6,padding:'2px',display:'flex'}}>
                          <XCircle size={16}/>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {appts.length===0&&(
                  <tr><td colSpan={6} style={{padding:'24px',textAlign:'center',color:'#94a3b8',fontSize:'.875rem'}}>No appointments today</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Calendar */}
        <div style={{background:'#fff',borderRadius:'16px',padding:'20px',boxShadow:'0 1px 8px rgba(0,0,0,.06)'}}>
          <h2 style={{fontSize:'.9375rem',fontWeight:700,color:'#0f172a',margin:'0 0 14px'}}>Calendar</h2>
          <MiniCalendar appointmentDates={appts.map(a=>a.scheduled_at)}/>
        </div>
      </div>

      {/* Chart */}
      <div style={{background:'#fff',borderRadius:'16px',padding:'20px',boxShadow:'0 1px 8px rgba(0,0,0,.06)'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'14px'}}>
          <h2 style={{fontSize:'.9375rem',fontWeight:700,color:'#0f172a',margin:0}}>Weekly Appointments</h2>
          <div style={{display:'flex',gap:'16px'}}>
            {[{color:'#3b82f6',label:'F10 Clinic'},{color:'#10b981',label:'Bahria Phase 4'}].map(({color,label})=>(
              <div key={label} style={{display:'flex',alignItems:'center',gap:'6px',fontSize:'.75rem',color:'#64748b'}}>
                <div style={{width:'10px',height:'10px',borderRadius:'3px',background:color}}/>{label}
              </div>
            ))}
          </div>
        </div>
        <BarChart data={WEEKLY}/>
      </div>
    </>
  )
}
