import React from "react";
import { Contrast, ALargeSmall, Type, AlignJustify, Volume2, VolumeX } from "lucide-react";

export const defaultA11y = { contrast: false, large: false, dyslexia: false, spacing: 1.5 };

export default function AccessibilityToolbar({ settings, onChange, readText }) {
  const [speaking, setSpeaking] = React.useState(false);
  const toggle = (k) => onChange({ ...settings, [k]: !settings[k] });

  const speak = () => {
    if (!("speechSynthesis" in window)) return alert("Read aloud is not supported in this browser.");
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(readText || "Nothing to read yet.");
    u.onend = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
    setSpeaking(true);
  };

  const Btn = ({ on, onClick, icon: Icon, label }) => (
    <button onClick={onClick} aria-pressed={on} className={`flex items-center gap-2 rounded-md border-2 px-3 py-2 font-bold ${on ? "border-teal-700 bg-teal-700 text-white" : "border-slate-300 bg-white"}`}>
      <Icon size={18} aria-hidden /> {label}
    </button>
  );

  return (
    <div role="toolbar" aria-label="Accessibility settings" className="sticky top-14 z-10 flex flex-wrap items-center gap-2 border-b border-stone-200 bg-white p-3">
      <Btn on={settings.contrast} onClick={() => toggle("contrast")} icon={Contrast} label="High contrast" />
      <Btn on={settings.large} onClick={() => toggle("large")} icon={ALargeSmall} label="Large text" />
      <Btn on={settings.dyslexia} onClick={() => toggle("dyslexia")} icon={Type} label="Dyslexia font" />
      <label className="flex items-center gap-2 font-bold">
        <AlignJustify size={18} aria-hidden /> Line spacing
        <input type="range" min="1.2" max="2.4" step="0.2" value={settings.spacing} onChange={(e) => onChange({ ...settings, spacing: Number(e.target.value) })} />
      </label>
      <Btn on={speaking} onClick={speak} icon={speaking ? VolumeX : Volume2} label={speaking ? "Stop" : "Read aloud"} />
    </div>
  );
}
