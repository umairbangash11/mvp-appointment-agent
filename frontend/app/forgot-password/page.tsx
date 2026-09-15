'use client'

import Link from 'next/link'

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-2xl p-8 shadow-2xl">
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Reset password</h2>
        <p className="text-gray-500 text-sm mb-6">
          Enter your email and we&apos;ll send you a reset link.
        </p>
        <input
          type="email"
          placeholder="doctor@clinic.com"
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent mb-4"
        />
        <button className="w-full py-3 bg-black text-white font-semibold rounded-lg hover:bg-zinc-800 transition text-sm mb-4">
          Send reset link
        </button>
        <p className="text-center text-sm text-gray-500">
          <Link href="/login" className="text-violet-600 hover:text-violet-700 font-medium">
            ← Back to login
          </Link>
        </p>
      </div>
    </div>
  )
}
