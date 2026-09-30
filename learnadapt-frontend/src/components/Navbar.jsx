import React from "react";
import { LogOut, LogIn, Repeat } from "lucide-react";

export default function Navbar({ user, onHome, onLogin, onLogout }) {
  return (
    <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3" aria-label="Main">
        <button onClick={onHome} className="flex items-center gap-2 text-lg font-bold text-teal-800">
          <Repeat size={22} aria-hidden /> LearnAdapt AI
        </button>
        <div className="flex items-center gap-4 text-sm">
          {!user && (
            <>
              <button onClick={onHome} className="hover:underline">Home</button>
              <a href="#loop" className="hover:underline">How it works</a>
              <a href="#accessibility" className="hover:underline">Accessibility</a>
            </>
          )}
          {user && (
            <span className="rounded-full bg-teal-100 px-3 py-1 font-bold capitalize text-teal-900">{user.role}</span>
          )}
          {user ? (
            <button onClick={onLogout} className="flex items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 hover:bg-stone-100">
              <LogOut size={16} aria-hidden /> Log out
            </button>
          ) : (
            <button onClick={() => onLogin()} className="flex items-center gap-1 rounded-md bg-teal-700 px-3 py-1.5 font-bold text-white hover:bg-teal-800">
              <LogIn size={16} aria-hidden /> Log in
            </button>
          )}
        </div>
      </nav>
    </header>
  );
}
