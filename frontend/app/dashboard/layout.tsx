'use client'

import { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, CalendarDays, Users, Settings, LogOut } from 'lucide-react'
import { authFetch } from '@/lib/api'

const navItems = [
  { label: 'Dashboard',    href: '/dashboard',              Icon: LayoutDashboard },
  { label: 'Appointments', href: '/dashboard/appointments', Icon: CalendarDays    },
  { label: 'Patients',     href: '/dashboard/patients',     Icon: Users           },
  { label: 'Settings',     href: '/dashboard/settings',     Icon: Settings        },
]

interface DoctorProfile { name: string; clinic_name: string }

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter()
  const pathname = usePathname()
  const [doctor, setDoctor] = useState<DoctorProfile>({ name: '', clinic_name: '' })

  useEffect(() => {
    authFetch('/auth/profile')
      .then(r => r.ok ? r.json() : null)
      .then((d: DoctorProfile | null) => { if (d) setDoctor(d) })
      .catch(() => {})
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    router.push('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f1f5f9', fontFamily: "system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" }}>

      {/* Sidebar */}
      <aside style={{
        width: '220px', flexShrink: 0,
        background: 'linear-gradient(180deg,#0f172a 0%,#1a3150 100%)',
        display: 'flex', flexDirection: 'column',
        position: 'sticky', top: 0, height: '100vh', overflowY: 'auto',
      }}>
        {/* Brand */}
        <div style={{ padding: '24px 20px 22px', borderBottom: '1px solid rgba(255,255,255,.07)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.125rem', flexShrink: 0 }}>🏥</div>
            <div>
              <div style={{ color: '#fff', fontWeight: 700, fontSize: '.9375rem', lineHeight: 1.2 }}>{doctor.name || 'Doctor'}</div>
              <div style={{ color: '#64748b', fontSize: '.6875rem', marginTop: '1px' }}>{doctor.clinic_name || 'Doctor Portal'}</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '18px 10px 0' }}>
          {navItems.map(({ label, href, Icon }) => {
            const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
            return (
              <button key={href} onClick={() => router.push(href)} style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                padding: '9px 12px', borderRadius: '10px', marginBottom: '3px',
                background: active ? 'rgba(59,130,246,.18)' : 'transparent',
                border: `1px solid ${active ? 'rgba(59,130,246,.25)' : 'transparent'}`,
                color: active ? '#60a5fa' : '#94a3b8',
                fontSize: '.875rem', fontWeight: active ? 600 : 400,
                cursor: 'pointer', textAlign: 'left', transition: 'all .15s',
              }}>
                <Icon size={15} />
                {label}
              </button>
            )
          })}
        </nav>

        {/* Logout */}
        <div style={{ padding: '12px 10px 20px' }}>
          <button onClick={handleLogout} style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
            padding: '9px 12px', borderRadius: '10px',
            background: 'transparent', border: '1px solid transparent',
            color: '#f87171', fontSize: '.875rem', cursor: 'pointer',
          }}>
            <LogOut size={15} />
            Logout
          </button>
        </div>
      </aside>

      {/* Page content */}
      <main style={{ flex: 1, padding: '28px 28px 40px', overflowY: 'auto', minWidth: 0 }}>
        {children}
      </main>
    </div>
  )
}
