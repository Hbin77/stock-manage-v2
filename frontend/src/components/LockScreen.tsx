"use client";

import { useState, useEffect, FormEvent } from "react";

const SITE_PASSWORD = process.env.NEXT_PUBLIC_SITE_PASSWORD;

export default function LockScreen({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);
  const [shake, setShake] = useState(false);

  useEffect(() => {
    // 비밀번호 미설정 시 잠금 없이 바로 통과
    if (!SITE_PASSWORD) {
      setUnlocked(true);
      return;
    }
    setUnlocked(sessionStorage.getItem("unlocked") === "true");
  }, []);

  // 초기 로딩 중 깜빡임 방지
  if (unlocked === null) return null;

  if (unlocked) return <>{children}</>;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input === SITE_PASSWORD) {
      sessionStorage.setItem("unlocked", "true");
      setUnlocked(true);
    } else {
      setError(true);
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950">
      <form
        onSubmit={handleSubmit}
        className={`w-full max-w-sm rounded-2xl bg-gray-900 p-8 shadow-2xl border border-gray-800 ${
          shake ? "animate-shake" : ""
        }`}
      >
        <h1 className="mb-2 text-center text-2xl font-bold text-white">
          🔒 잠금 화면
        </h1>
        <p className="mb-6 text-center text-sm text-gray-400">
          비밀번호를 입력하세요
        </p>

        <input
          type="password"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setError(false);
          }}
          placeholder="비밀번호"
          autoFocus
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-center text-lg tracking-widest text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        {error && (
          <p className="mt-2 text-center text-sm text-red-400">
            비밀번호가 틀렸습니다
          </p>
        )}

        <button
          type="submit"
          className="mt-4 w-full rounded-lg bg-blue-600 py-3 font-semibold text-white transition-colors hover:bg-blue-500"
        >
          확인
        </button>
      </form>
    </div>
  );
}
