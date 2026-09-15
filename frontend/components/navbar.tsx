"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { clearTokens } from "@/lib/auth";

interface NavbarProps {
  doctorName?: string;
  clinicName?: string;
}

const NAV_LINKS = [
  { href: "/dashboard",    label: "Dashboard" },
  { href: "/appointments", label: "Appointments" },
  { href: "/patients",     label: "Patients" },
  { href: "/settings",     label: "Settings" },
];

export default function Navbar({ doctorName, clinicName }: NavbarProps) {
  const router   = useRouter();
  const pathname = usePathname();

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-bold">+</span>
        </div>
        <div>
          <p className="font-semibold text-gray-900">{doctorName || "Doctor"}</p>
          {clinicName && <p className="text-xs text-gray-500">{clinicName}</p>}
        </div>
      </div>

      <nav className="flex items-center gap-1">
        {NAV_LINKS.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:text-blue-600 hover:bg-gray-50"
              }`}
            >
              {label}
            </Link>
          );
        })}
        <Link
          href="/whatsapp-test"
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-green-600 hover:bg-green-50 transition"
        >
          WhatsApp Test
        </Link>
        <button
          onClick={logout}
          className="ml-2 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 transition"
        >
          Logout
        </button>
      </nav>
    </header>
  );
}
