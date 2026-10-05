import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import "./index.css";
import Campaign from "./pages/Campaign";
import Check from "./pages/Check";
import Home from "./pages/Home";
import Share from "./pages/Share";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex max-w-[40rem] items-center px-4 pt-5">
        <Link to="/" className="text-[1.05rem] font-extrabold tracking-tight text-ink no-underline">
          Special<span className="text-action">26</span>
        </Link>
      </header>
      <main className="mx-auto max-w-[40rem] px-4 pb-24 pt-6">{children}</main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/c/:id" element={<Check />} />
            <Route path="/s/:token" element={<Share />} />
            <Route path="/campaign/:id" element={<Campaign />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
