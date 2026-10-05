import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { ERRORS, rateLimited } from "../copy";
import { EXAMPLES } from "../examples";

type Role = "offer_pdf" | "offer_image" | "eml" | "hr_photo";
const UPLOADS: { role: Role | "letter"; label: string; accept: string; help?: string }[] = [
  { role: "letter", label: "Offer letter (PDF or screenshot)", accept: ".pdf,image/png,image/jpeg" },
  { role: "eml", label: "Original email (.eml)", accept: ".eml,message/rfc822",
    help: "Gmail: open the email, tap ⋮, Download message." },
  { role: "hr_photo", label: "HR's profile photo", accept: "image/png,image/jpeg" },
];
const MAX = 5 * 1024 * 1024;

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "RATE_LIMITED") return rateLimited(Math.max(1, Math.ceil((e.retryAfter ?? 60) / 60)));
    return ERRORS[e.code] ?? e.message;
  }
  return "Couldn't reach Special26. Check your connection and try again.";
}

export default function Home() {
  const nav = useNavigate();
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Partial<Record<string, File>>>({});
  const [error, setError] = useState<string | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const create = useMutation({
    mutationFn: () => {
      const form = new FormData();
      if (text.trim()) form.append("text", text);
      const roles: Role[] = [];
      for (const [role, f] of Object.entries(files)) {
        if (!f) continue;
        form.append("files", f);
        roles.push(role === "letter" ? (f.type === "application/pdf" ? "offer_pdf" : "offer_image") : (role as Role));
      }
      form.append("file_roles", JSON.stringify(roles));
      return api.create(form);
    },
    onSuccess: (c) => nav(`/c/${c.check_id}`),
    onError: (e) => setError(errorText(e)),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() && !Object.values(files).some(Boolean)) {
      setError(ERRORS.empty);
      textRef.current?.focus();
      return;
    }
    setError(null);
    create.mutate();
  }

  function pick(role: string, f: File | undefined) {
    if (f && f.size > MAX) return setError(ERRORS.PAYLOAD_TOO_LARGE);
    setError(null);
    setFiles((prev) => ({ ...prev, [role]: f }));
  }

  return (
    <form onSubmit={submit} noValidate>
      <h1 className="text-balance text-[2rem] font-extrabold leading-[1.1] tracking-tight sm:text-[2.6rem]">
        Got an internship or job offer? Check it before you pay or share documents.
      </h1>
      <p className="mt-4 max-w-[34rem] text-[1.05rem] leading-relaxed text-muted">
        Paste the message or upload the offer letter. We check the sender, the company, the office, the HR photo and
        the payment ask against Google, Maps, Jobs and Lens.
      </p>

      <label htmlFor="offer" className="sr-only">Offer text</label>
      <textarea
        id="offer" ref={textRef} value={text} onChange={(e) => setText(e.target.value)} rows={9}
        placeholder="Paste the WhatsApp message, email or offer letter text here"
        aria-invalid={!!error} aria-describedby={error ? "form-error" : undefined}
        className="mt-7 block w-full resize-y rounded-lg border border-rule bg-surface p-4 text-[1rem] leading-relaxed shadow-[inset_0_1px_2px_rgb(28_36_51/0.06)] placeholder:text-[#8a93a3] focus:border-action focus:outline-none"
      />

      <div className="mt-3 flex flex-wrap gap-2" aria-label="Load an example">
        {EXAMPLES.map((x) => (
          <button key={x.label} type="button" onClick={() => { setText(x.text); setError(null); }}
            className="rounded-full border border-rule bg-surface px-3 py-1.5 text-[0.85rem] text-ink hover:border-action">
            {x.label}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-3">
        {UPLOADS.map((u) => {
          const f = files[u.role];
          return (
            <div key={u.role}>
              <label className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-dashed border-[#b9bfca] bg-surface px-4 py-3 hover:border-action">
                <span className="text-[0.95rem] font-semibold">{u.label}</span>
                <span className="truncate text-[0.85rem] text-muted">{f ? f.name : "Choose file"}</span>
                <input type="file" accept={u.accept} className="sr-only"
                  onChange={(e) => pick(u.role, e.target.files?.[0])} />
              </label>
              {u.help && <p className="mt-1 pl-1 text-[0.82rem] text-muted">{u.help}</p>}
            </div>
          );
        })}
      </div>

      {error && <p id="form-error" role="alert" className="mt-4 font-semibold text-red">{error}</p>}

      <button type="submit" disabled={create.isPending}
        className="mt-6 w-full rounded-lg bg-action px-5 py-4 text-[1.05rem] font-bold text-white hover:bg-action-dark disabled:opacity-60 sm:w-auto">
        {create.isPending ? "Reading the offer…" : "Check this offer"}
      </button>

      <p className="mt-8 text-[0.85rem] text-muted">
        We never contact the sender. Your name, phone and email are removed before anything is stored.
      </p>
    </form>
  );
}
