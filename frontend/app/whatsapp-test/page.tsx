"use client";

import { useRef, useState } from "react";
import Link from "next/link";

interface ChatMessage {
  id: string;
  sender: "patient" | "agent";
  text?: string;
  audioBase64?: string;
  isVoice?: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function newId() {
  return Math.random().toString(36).slice(2);
}

export default function WhatsAppTestPage() {
  const [phone] = useState(() => `whatsapp:+971sim${Math.floor(Math.random() * 1e8)}`);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function sendText() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { id: newId(), sender: "patient", text }]);
    setSending(true);
    try {
      const form = new FormData();
      form.append("phone", phone);
      form.append("text", text);
      const res = await fetch(`${API_URL}/whatsapp/simulate`, { method: "POST", body: form });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { id: newId(), sender: "agent", text: data.reply_text, audioBase64: data.audio_base64 },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: newId(), sender: "agent", text: "(Error reaching the WhatsApp agent — is the backend running?)" },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        sendVoiceNote(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: newId(), sender: "agent", text: "(Microphone access denied or unavailable.)" },
      ]);
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  async function sendVoiceNote(blob: Blob) {
    const localUrl = URL.createObjectURL(blob);
    setMessages((prev) => [
      ...prev,
      { id: newId(), sender: "patient", audioBase64: localUrl, isVoice: true },
    ]);
    setSending(true);
    try {
      const form = new FormData();
      form.append("phone", phone);
      form.append("audio", blob, "voice-note.webm");
      const res = await fetch(`${API_URL}/whatsapp/simulate`, { method: "POST", body: form });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          sender: "agent",
          text: data.reply_text,
          audioBase64: data.audio_base64 ? `data:audio/mpeg;base64,${data.audio_base64}` : undefined,
          isVoice: true,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: newId(), sender: "agent", text: "(Error reaching the WhatsApp agent — is the backend running?)" },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#e5ddd5]">
      <header className="bg-[#075E54] text-white px-6 py-4 flex items-center justify-between shadow">
        <div>
          <p className="font-semibold">WhatsApp Booking Simulator</p>
          <p className="text-xs text-[#d1f4ec]">Dev/test tool — not authenticated, not for patient use</p>
        </div>
        <Link href="/dashboard" className="text-sm text-white/90 hover:underline">
          Back to Dashboard
        </Link>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto flex flex-col px-4 py-6 gap-3 overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-center text-gray-500 text-sm mt-10">
            Type a message or record a voice note to start the booking flow (Arabic or English).
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.sender === "agent" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-lg px-3 py-2 shadow text-sm ${
                m.sender === "agent" ? "bg-[#25D366] text-white" : "bg-white text-gray-900"
              }`}
              dir="auto"
            >
              {m.text && <p className="whitespace-pre-wrap">{m.text}</p>}
              {m.audioBase64 && (
                <audio controls autoPlay={m.sender === "agent"} className="mt-1 max-w-full">
                  <source src={m.audioBase64} />
                </audio>
              )}
            </div>
          </div>
        ))}
      </main>

      <footer className="bg-[#f0f0f0] border-t border-gray-300 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendText()}
            placeholder="Type a message..."
            className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#25D366]"
            disabled={sending || recording}
          />
          <button
            onClick={recording ? stopRecording : startRecording}
            className={`w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0 ${
              recording ? "bg-red-500 animate-pulse" : "bg-[#075E54]"
            }`}
            title={recording ? "Stop recording" : "Record voice note"}
            disabled={sending}
          >
            🎤
          </button>
          <button
            onClick={sendText}
            className="w-10 h-10 rounded-full bg-[#25D366] text-white flex items-center justify-center shrink-0 disabled:opacity-50"
            disabled={sending || recording || !input.trim()}
            title="Send"
          >
            ➤
          </button>
        </div>
      </footer>
    </div>
  );
}
