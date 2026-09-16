'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Save } from 'lucide-react'
import { authFetch } from '@/lib/api'

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '.625rem .75rem',
  border: '1px solid #e2e8f0', borderRadius: '8px',
  fontSize: '.875rem', color: '#1e293b', outline: 'none',
  background: '#fff', fontFamily: 'inherit',
}
const disabledInput: React.CSSProperties = {
  ...inputStyle, background: '#f8fafc', color: '#94a3b8', cursor: 'not-allowed',
}
const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: '.75rem', fontWeight: 600,
  color: '#64748b', marginBottom: '.3rem',
}

export default function SettingsPage() {
  const router = useRouter()
  const [profile, setProfile] = useState({ name: '', email: '', clinic_name: '', phone: '', state: '' })
  const [pwForm,  setPwForm]  = useState({ current_password: '', new_password: '', confirm: '' })
  const [showPw,  setShowPw]  = useState({ current: false, new: false, confirm: false })
  const [saving,  setSaving]  = useState(false)
  const [pwSaving, setPwSaving] = useState(false)
  const [msg,     setMsg]     = useState('')
  const [pwMsg,   setPwMsg]   = useState('')
  const [ready,   setReady]   = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('token')) { router.push('/login'); return }
    setReady(true)
    authFetch('/auth/profile')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setProfile({ name: d.name ?? '', email: d.email ?? '', clinic_name: d.clinic_name ?? '', phone: d.phone ?? '', state: d.state ?? '' }) })
      .catch(() => {})
  }, [router])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setProfile(prev => ({ ...prev, [e.target.name]: e.target.value }))

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setMsg('')
    try {
      const res = await authFetch('/auth/profile/update', {
        method: 'PUT',
        body: JSON.stringify({ name: profile.name, clinic_name: profile.clinic_name, phone: profile.phone, state: profile.state }),
      })
      setMsg(res.ok ? '✓ Profile updated successfully' : 'Failed to update profile')
    } catch { setMsg('Network error') }
    finally { setSaving(false) }
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault(); setPwMsg('')
    if (pwForm.new_password !== pwForm.confirm) { setPwMsg('Passwords do not match'); return }
    if (pwForm.new_password.length < 8) { setPwMsg('Password must be at least 8 characters'); return }
    setPwSaving(true)
    try {
      const res = await authFetch('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: pwForm.current_password, new_password: pwForm.new_password }),
      })
      const data = await res.json()
      if (res.ok) {
        setPwMsg('✓ Password changed successfully')
        setPwForm({ current_password: '', new_password: '', confirm: '' })
      } else {
        const d = data.detail
        setPwMsg(Array.isArray(d) ? d.map((x: {msg?:string}) => x.msg).join(', ') : typeof d === 'string' ? d : 'Failed to change password')
      }
    } catch { setPwMsg('Network error') }
    finally { setPwSaving(false) }
  }

  if (!ready) return null

  const isSuccess = (s: string) => s.startsWith('✓')

  return (
    <>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>Settings</h1>
        <p style={{ color: '#64748b', fontSize: '.8125rem', margin: '4px 0 0' }}>Manage your profile and account</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', alignItems: 'start' }}>

        {/* Profile form */}
        <div style={{ background: '#fff', borderRadius: '16px', padding: '24px', boxShadow: '0 1px 8px rgba(0,0,0,.06)' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: '0 0 20px' }}>Profile Information</h2>

          {msg && (
            <div style={{ padding: '.625rem .875rem', borderRadius: '8px', fontSize: '.8125rem', marginBottom: '16px',
              background: isSuccess(msg) ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)',
              color:      isSuccess(msg) ? '#059669'             : '#dc2626',
              border:     `1px solid ${isSuccess(msg) ? 'rgba(16,185,129,.2)' : 'rgba(239,68,68,.2)'}`,
            }}>{msg}</div>
          )}

          <form onSubmit={saveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={labelStyle}>Full Name</label>
              <input name="name" type="text" value={profile.name} onChange={handleChange} required style={inputStyle} placeholder="Dr. Wasim Ahmed" />
            </div>
            <div>
              <label style={labelStyle}>Email <span style={{ color: '#cbd5e1', fontWeight: 400 }}>(read-only)</span></label>
              <input type="email" value={profile.email} readOnly style={disabledInput} />
            </div>
            <div>
              <label style={labelStyle}>Clinic Name</label>
              <input name="clinic_name" type="text" value={profile.clinic_name} onChange={handleChange} required style={inputStyle} placeholder="Your clinic name" />
            </div>
            <div>
              <label style={labelStyle}>Phone</label>
              <input name="phone" type="tel" value={profile.phone} onChange={handleChange} style={inputStyle} placeholder="+92 300 0000000" />
            </div>
            <div>
              <label style={labelStyle}>City / State</label>
              <input name="state" type="text" value={profile.state} onChange={handleChange} style={inputStyle} placeholder="Islamabad" />
            </div>
            <button type="submit" disabled={saving} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
              padding: '.75rem', background: '#0f172a', color: '#fff',
              border: 'none', borderRadius: '10px', fontSize: '.875rem', fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? .6 : 1,
              fontFamily: 'inherit', marginTop: '4px',
            }}>
              <Save size={15} />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        </div>

        {/* Change password */}
        <div style={{ background: '#fff', borderRadius: '16px', padding: '24px', boxShadow: '0 1px 8px rgba(0,0,0,.06)' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', margin: '0 0 20px' }}>Change Password</h2>

          {pwMsg && (
            <div style={{ padding: '.625rem .875rem', borderRadius: '8px', fontSize: '.8125rem', marginBottom: '16px',
              background: isSuccess(pwMsg) ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)',
              color:      isSuccess(pwMsg) ? '#059669'             : '#dc2626',
              border:     `1px solid ${isSuccess(pwMsg) ? 'rgba(16,185,129,.2)' : 'rgba(239,68,68,.2)'}`,
            }}>{pwMsg}</div>
          )}

          <form onSubmit={changePassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {([
              { key: 'current_password', label: 'Current Password',  show: showPw.current, toggle: () => setShowPw(s=>({...s,current:!s.current})) },
              { key: 'new_password',     label: 'New Password',      show: showPw.new,     toggle: () => setShowPw(s=>({...s,new:!s.new})) },
              { key: 'confirm',          label: 'Confirm Password',  show: showPw.confirm, toggle: () => setShowPw(s=>({...s,confirm:!s.confirm})) },
            ] as const).map(({ key, label, show, toggle }) => (
              <div key={key}>
                <label style={labelStyle}>{label}</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={show ? 'text' : 'password'}
                    value={pwForm[key]}
                    onChange={e => setPwForm(prev => ({ ...prev, [key]: e.target.value }))}
                    required minLength={key === 'current_password' ? 1 : 8}
                    placeholder="••••••••"
                    style={{ ...inputStyle, paddingRight: '2.5rem' }}
                  />
                  <button type="button" onClick={toggle} style={{ position: 'absolute', right: '.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 0, display: 'flex' }}>
                    {show ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
            ))}

            <button type="submit" disabled={pwSaving} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
              padding: '.75rem', background: '#0f172a', color: '#fff',
              border: 'none', borderRadius: '10px', fontSize: '.875rem', fontWeight: 600,
              cursor: pwSaving ? 'not-allowed' : 'pointer', opacity: pwSaving ? .6 : 1,
              fontFamily: 'inherit', marginTop: '4px',
            }}>
              {pwSaving ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>

      </div>
    </>
  )
}
