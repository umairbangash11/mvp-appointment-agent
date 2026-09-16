'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const card: React.CSSProperties = {
  background: '#1a1a1a',
  borderRadius: '20px',
  padding: '1.75rem',
  border: '1px solid rgba(255,255,255,.08)',
  width: '100%',
  maxWidth: '400px',
  position: 'relative',
  zIndex: 10,
}

const input: React.CSSProperties = {
  width: '100%',
  padding: '.625rem .75rem',
  background: '#111',
  border: '1px solid rgba(255,255,255,.12)',
  borderRadius: '8px',
  fontSize: '.875rem',
  color: '#fff',
  outline: 'none',
  fontFamily: 'inherit',
}

const label: React.CSSProperties = {
  display: 'block',
  fontSize: '.75rem',
  fontWeight: 500,
  color: '#999',
  marginBottom: '.3rem',
}

const primaryBtn: React.CSSProperties = {
  width: '100%',
  padding: '.75rem',
  background: '#fff',
  color: '#000',
  fontSize: '.875rem',
  fontWeight: 600,
  border: 'none',
  borderRadius: '10px',
  cursor: 'pointer',
  fontFamily: 'inherit',
  marginTop: '.125rem',
}

const socialBtn: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '.5rem',
  padding: '.625rem .5rem',
  background: '#222',
  border: '1px solid rgba(255,255,255,.1)',
  borderRadius: '10px',
  fontSize: '.8125rem',
  fontWeight: 500,
  color: '#fff',
  cursor: 'pointer',
  fontFamily: 'inherit',
}

const glowBase: React.CSSProperties = {
  position: 'fixed',
  borderRadius: '50%',
  pointerEvents: 'none',
}

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        const detail = data.detail
        const msg = Array.isArray(detail)
          ? detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(', ')
          : typeof detail === 'string' ? detail : 'Invalid email or password'
        setError(msg)
      } else {
        localStorage.setItem('token', data.access_token)
        if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
        router.push('/dashboard')
      }
    } catch {
      setError('Network error. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', overflow: 'hidden', position: 'relative' }}>

      {/* ── Glow circles ── */}
      <div style={{ ...glowBase, bottom: '-90px', right: '-50px',  width: '360px', height: '360px', background: 'rgba(255,45,85,.6)',   filter: 'blur(110px)' }} />
      <div style={{ ...glowBase, bottom: '70px',  right: '170px',  width: '270px', height: '270px', background: 'rgba(59,130,246,.55)', filter: 'blur(90px)' }} />
      <div style={{ ...glowBase, bottom: '-10px', right: '260px',  width: '210px', height: '210px', background: 'rgba(16,185,129,.45)', filter: 'blur(80px)' }} />

      {/* ── Card ── */}
      <div style={card}>

        {/* Tabs */}
        <div style={{ display: 'flex', background: '#111', borderRadius: '10px', padding: '3px', marginBottom: '1.375rem' }}>
          <Link href="/signup" style={{ flex: 1, padding: '.5rem', textAlign: 'center', borderRadius: '7px', color: '#666', fontSize: '.875rem', fontWeight: 500, textDecoration: 'none', display: 'block' }}>
            Sign up
          </Link>
          <div style={{ flex: 1, padding: '.5rem', textAlign: 'center', borderRadius: '7px', background: '#fff', color: '#000', fontSize: '.875rem', fontWeight: 600 }}>
            Sign in
          </div>
        </div>

        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '.25rem' }}>Welcome back</h2>
        <p style={{ fontSize: '.8125rem', color: '#666', marginBottom: '1.25rem' }}>Sign in to your doctor portal</p>

        {error && (
          <div style={{ padding: '.625rem .75rem', background: 'rgba(220,38,38,.15)', border: '1px solid rgba(220,38,38,.3)', color: '#f87171', fontSize: '.8125rem', borderRadius: '8px', marginBottom: '.875rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>

          {/* Email */}
          <div>
            <label style={label}>Email</label>
            <input type="email" placeholder="doctor@clinic.com" value={email} onChange={e => setEmail(e.target.value)} required style={input} />
          </div>

          {/* Password */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '.3rem' }}>
              <label style={{ ...label, marginBottom: 0 }}>Password</label>
              <Link href="/forgot-password" style={{ fontSize: '.75rem', color: '#666', textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </div>
            <div style={{ position: 'relative' }}>
              <input type={showPw ? 'text' : 'password'} placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required style={{ ...input, paddingRight: '2.5rem' }} />
              <button type="button" onClick={() => setShowPw(v => !v)} style={{ position: 'absolute', right: '.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#666', padding: 0, display: 'flex' }}>
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button type="submit" disabled={loading} style={{ ...primaryBtn, opacity: loading ? .6 : 1 }}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '.625rem', margin: '.875rem 0' }}>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,.08)' }} />
          <span style={{ fontSize: '.75rem', color: '#555' }}>or</span>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,.08)' }} />
        </div>

        {/* Social buttons */}
        <div style={{ display: 'flex', gap: '.625rem' }}>
          <button type="button" style={socialBtn}><AppleIcon /> Apple</button>
          <button type="button" style={socialBtn}><GoogleIcon /> Google</button>
        </div>

        <p style={{ textAlign: 'center', fontSize: '.875rem', color: '#555', marginTop: '1rem' }}>
          Don&apos;t have an account?{' '}
          <Link href="/signup" style={{ color: '#aaa', textDecoration: 'none', fontWeight: 500 }}>Sign up</Link>
        </p>
      </div>
    </div>
  )
}

function AppleIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 814 1000" fill="currentColor">
      <path d="M788.1 340.9c-5.8 4.5-108.2 62.2-108.2 190.5 0 148.4 130.3 200.9 134.2 202.2-.6 3.2-20.7 71.9-68.7 141.9-42.8 61.6-87.5 123.1-155.5 123.1s-85.5-39.5-164-39.5c-76 0-103.7 40.8-165.9 40.8s-105-57.8-155.5-127.4C46 790.8 0 689.3 0 592.8 0 395.1 134.4 290.2 266.4 290.2c66.4 0 121.7 43.3 164 43.3 40.4 0 103.9-45.5 177.6-45.5 28.4 0 130.9 2.6 198.3 99z"/>
      <path d="M512.7 92.6C548.5 51.4 574 8.6 574 0c0-1.3 0-2.6-.6-3.8-1.9-.6-4.5-1.3-6.4-1.3-31.4 0-67.9 25.7-96.3 60.8-27.8 34.5-54.9 93.3-48.1 150.2 1.3 1.3 2.6 1.9 3.8 1.9 30.8 0 68-26.3 85.3-115.2z"/>
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}
