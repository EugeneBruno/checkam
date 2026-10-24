import { useMemo, useState } from "react";
import {
  Bookmark,
  Check,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleHelp,
  CircleX,
  Flag,
  Grid2X2,
  History,
  Info,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PackageSearch,
  Plug,
  Search,
  ScanLine,
  Settings,
  TriangleAlert,
} from "lucide-react";
import checkAmLogo from "../public/Check_Am_Logo-removebg-preview.png";

const recentChecks = [
  {
    id: 1,
    product: "Ilera Demo Relief",
    finding: "Label and public record align",
    date: "23 Oct · 10:42",
    verdict: "Likely genuine",
    trust: "84",
    icon: "pill",
  },
  {
    id: 2,
    product: "Ilera Demo Relief",
    finding: "Registry number belongs to another product",
    date: "23 Oct · 09:18",
    verdict: "Likely fake",
    trust: "18",
    icon: "pill",
  },
  {
    id: 3,
    product: "Ilera Demo Relief",
    finding: "Different expiry recorded in Kano",
    date: "22 Oct · 16:35",
    verdict: "Likely fake",
    trust: "12",
    icon: "pill",
  },
  {
    id: 4,
    product: "Ilera Demo Relief",
    finding: "Reported by 1 other buyer",
    date: "22 Oct · 12:06",
    verdict: "Suspicious",
    trust: "52",
    icon: "pill",
  },
  {
    id: 5,
    product: "Kora Demo Kettle",
    finding: "SON mark present; SMS check still needed",
    date: "21 Oct · 14:28",
    verdict: "Be careful",
    trust: "68",
    icon: "plug",
  },
  {
    id: 6,
    product: "Mora Demo Botanical Balm",
    finding: "Rear label needed to identify maker",
    date: "20 Oct · 11:04",
    verdict: "Not enough evidence",
    trust: "—",
    icon: "package",
  },
];

const verdictStyles = {
  "Likely genuine": {
    Icon: CircleCheck,
    classes: "bg-[#E7F0E8] text-[#18543F]",
  },
  "Likely fake": {
    Icon: CircleX,
    classes: "bg-[#FCECEC] text-[#A93434]",
  },
  Suspicious: {
    Icon: TriangleAlert,
    classes: "bg-[#FFF1D8] text-[#9B5B10]",
  },
  "Be careful": {
    Icon: TriangleAlert,
    classes: "bg-[#FFF1D8] text-[#9B5B10]",
  },
  "Not enough evidence": {
    Icon: CircleHelp,
    classes: "bg-[#EEF1F0] text-[#66736D]",
  },
};

function ProductIcon({ type }) {
  const Icon = type === "plug" ? Plug : type === "package" ? PackageSearch : Check;

  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[#E7F0E8] text-[#18543F]">
      <Icon size={17} strokeWidth={1.7} />
    </span>
  );
}

function VerdictBadge({ verdict }) {
  const { Icon, classes } = verdictStyles[verdict];

  return (
    <span className={`inline-flex w-fit items-center gap-1 rounded-full px-2 py-1 text-[10px] font-medium ${classes}`}>
      <Icon size={12} strokeWidth={1.8} />
      {verdict}
    </span>
  );
}

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(() =>
    window.matchMedia("(min-width: 768px)").matches,
  );
  const [search, setSearch] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("All verdicts");
  const [dateFilter, setDateFilter] = useState("All dates");

  const visibleChecks = useMemo(() => {
    const query = search.trim().toLowerCase();

    return recentChecks.filter((check) => {
      const matchesSearch =
        !query ||
        `${check.product} ${check.finding} ${check.verdict}`
          .toLowerCase()
          .includes(query);
      const matchesVerdict =
        verdictFilter === "All verdicts" || check.verdict === verdictFilter;

      return matchesSearch && matchesVerdict;
    });
  }, [search, verdictFilter]);

  return (
    <div className="min-h-screen bg-[#F7F7F0] font-medium text-[#203C32]">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close dashboard navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/20 md:hidden"
        />
      )}
      <aside
        id="dashboard-sidebar"
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh w-[min(18rem,85vw)] flex-col overflow-y-auto bg-[#123E30] px-4 py-5 text-[#E5EEE8] shadow-xl transition-transform duration-300 ease-in-out motion-reduce:transition-none md:w-60 md:shadow-none ${
          sidebarOpen ? "translate-x-0" : "-translate-x-[calc(100%-3.5rem)]"
        }`}
      >
        {sidebarOpen && (
          <>
            <div className="mb-6 flex h-12 shrink-0 items-center justify-between gap-3">
              <a href="/" aria-label="Checkam home" className="flex h-12 min-w-0 items-center rounded-md bg-white px-2.5">
                <img
                  src={checkAmLogo}
                  alt="Checkam"
                  className="h-10 max-w-full object-contain object-left"
                />
              </a>
              <button
                type="button"
                aria-label="Close dashboard navigation"
                aria-expanded={sidebarOpen}
                aria-controls="dashboard-sidebar"
                onClick={() => setSidebarOpen(false)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#BCD0C1] transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                <PanelLeftClose size={19} />
              </button>
            </div>

            <nav aria-label="Dashboard" className="flex flex-col gap-1">
              <a href="/dashboard" className="flex shrink-0 items-center gap-2 rounded-md bg-[#2A5A47] px-2.5 py-2.5 text-[13px] text-white">
                <Grid2X2 size={14} />
                Overview
              </a>
              <a href="#recent-checks" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[13px] hover:bg-white/10">
                <History size={14} />
                Scan history
              </a>
              <a href="#buyer-report" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[13px] hover:bg-white/10">
                <Flag size={14} />
                My reports
              </a>
              <a href="#recent-checks" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[13px] hover:bg-white/10">
                <Bookmark size={14} />
                Saved products
              </a>
            </nav>

            <div className="mt-5 rounded-md bg-[#204D3C] p-3">
              <ScanLine size={16} className="mb-2 text-[#BCD0C1]" />
              <p className="text-[13px] font-medium text-white">A second look is free.</p>
              <p className="mt-2 text-[12px] leading-relaxed text-[#BCD0C1]">
                Add a clearer photo to any check when you have the pack in your hands.
              </p>
            </div>

            <nav aria-label="Account" className="mt-auto flex flex-col gap-1 pt-5">
              <a href="/login" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[12px] hover:bg-white/10">
                <Settings size={13} />
                Account settings
              </a>
              <a href="#dashboard-disclaimer" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[12px] hover:bg-white/10">
                <CircleHelp size={13} />
                Help &amp; limits
              </a>
              <a href="/" className="flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2.5 text-[12px] hover:bg-white/10">
                <LogOut size={13} />
                Sign out
              </a>
            </nav>
          </>
        )}
        {!sidebarOpen && (
          <button
            type="button"
            aria-label="Open dashboard navigation"
            aria-expanded={sidebarOpen}
            aria-controls="dashboard-sidebar"
            onClick={() => setSidebarOpen(true)}
            className="absolute right-3 top-4 flex h-8 w-8 items-center justify-center rounded-md text-[#E5EEE8] transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <PanelLeftOpen size={19} />
          </button>
        )}
      </aside>

      <main className="min-w-0 px-5 pb-8 pt-6 sm:px-7 md:ml-60 md:px-7 lg:px-8">
        <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="mb-5 text-xs text-[#64746B]">Your space / Overview</p>
            <h1 className="text-3xl font-semibold tracking-tight text-[#123E30]">
              Good morning, Amara.
            </h1>
            <p className="mt-1 text-sm text-[#64746B]">
              Your checks, the evidence behind them, and what to look at next.
            </p>
          </div>
          <div className="flex items-center justify-between gap-4 sm:justify-end">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-[#EEF0EA] px-2.5 py-1 text-[11px] text-[#64746B]">
                Sample account
              </span>
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#E7F0E8] text-[11px] font-semibold text-[#18543F]">
                AO
              </span>
              <span className="text-xs">Amara O.</span>
            </div>
            <a
              href="/scan"
              className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-[#18543F] px-3 text-xs font-medium text-white transition-colors hover:bg-[#123E30]"
            >
              <ScanLine size={14} />
              New check
            </a>
          </div>
        </header>

        <section aria-label="Account summary" className="mb-4 grid gap-3 sm:grid-cols-3">
          <div className="flex min-h-15.5 items-center gap-3 rounded-xl border border-[#E0E5DC] bg-white px-4 py-3">
            <span className="text-[30px] font-medium leading-none text-[#18543F]">6</span>
            <div>
              <p className="text-xs font-medium">Saved checks</p>
              <p className="mt-0.5 text-[11px] text-[#64746B]">All time · sample</p>
            </div>
          </div>
          <div className="flex min-h-15.5 items-center gap-3 rounded-xl border border-[#E0E5DC] bg-white px-4 py-3">
            <span className="text-[30px] font-medium leading-none text-[#18543F]">3</span>
            <div>
              <p className="text-xs font-medium">Follow-up photos</p>
              <p className="mt-0.5 text-[11px] text-[#64746B]">More evidence would help</p>
            </div>
          </div>
          <div className="flex min-h-15.5 items-center gap-3 rounded-xl border border-[#E0E5DC] bg-white px-4 py-3">
            <span className="text-[30px] font-medium leading-none text-[#18543F]">2</span>
            <div>
              <p className="text-xs font-medium">Your reports</p>
              <p className="mt-0.5 text-[11px] text-[#64746B]">1 submitted · 1 draft</p>
            </div>
          </div>
        </section>

        <section aria-label="Recent activity" className="mb-4 grid gap-3 lg:grid-cols-2">
          <article className="flex gap-3 rounded-xl bg-[#FCEEEE] p-4 text-[#9D3636]">
            <CircleX size={16} className="mt-0.5 shrink-0" />
            <div>
              <h2 className="text-[13px] font-semibold">Same batch. Different expiry.</h2>
              <p className="mt-1 text-xs leading-relaxed text-[#684848]">
                Demo batch ILR-24B: your pack shows 08/2027; a Kano scan says 02/2026. Don’t use this pack.
              </p>
              <a href="#recent-checks" className="mt-1.5 inline-flex items-center text-[11px] font-medium hover:underline">
                Review sample history <ChevronRight size={11} />
              </a>
            </div>
          </article>
          <article id="buyer-report" className="flex gap-3 rounded-xl bg-[#FFF2DB] p-4 text-[#9B5B10]">
            <MessageSquare size={16} className="mt-0.5 shrink-0" />
            <div>
              <h2 className="text-[13px] font-semibold">A buyer flagged a batch you checked.</h2>
              <p className="mt-1 text-xs leading-relaxed text-[#635743]">
                1 other buyer reported demo batch ILR-24C. This is a buyer observation, not a confirmed counterfeit finding.
              </p>
              <a href="#recent-checks" className="mt-1.5 inline-flex items-center text-[11px] font-medium hover:underline">
                View buyer report <ChevronRight size={11} />
              </a>
            </div>
          </article>
        </section>

        <section id="recent-checks" className="rounded-xl border border-[#E0E5DC] bg-white p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-[#203C32]">Your recent checks</h2>
            <a href="#recent-checks" className="inline-flex items-center text-[11px] font-medium text-[#18543F] hover:underline">
              View scan history <ChevronRight size={12} />
            </a>
          </div>

          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-md border border-[#E0E5DC] px-2.5 text-[#18543F]">
              <Search size={14} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search product, batch or identifier"
                className="min-w-0 flex-1 bg-transparent text-[11px] text-[#203C32] outline-none placeholder:text-[#7A8980]"
                aria-label="Search product, batch or identifier"
              />
            </label>
            <label className="relative flex h-9 items-center rounded-md bg-[#F7F7F0] px-2.5 text-[11px]">
              <select
                value={verdictFilter}
                onChange={(event) => setVerdictFilter(event.target.value)}
                className="appearance-none bg-transparent pr-5 text-[#203C32] outline-none"
                aria-label="Filter by verdict"
              >
                <option>All verdicts</option>
                {Object.keys(verdictStyles).map((verdict) => (
                  <option key={verdict}>{verdict}</option>
                ))}
              </select>
              <ChevronDown size={12} className="pointer-events-none absolute right-2" />
            </label>
            <label className="relative flex h-9 items-center rounded-md bg-[#F7F7F0] px-2.5 text-[11px]">
              <select
                value={dateFilter}
                onChange={(event) => setDateFilter(event.target.value)}
                className="appearance-none bg-transparent pr-5 text-[#203C32] outline-none"
                aria-label="Filter by date"
              >
                <option>All dates</option>
                <option>Last 7 days</option>
              </select>
              <ChevronDown size={12} className="pointer-events-none absolute right-2" />
            </label>
            <span className="px-1 font-['IBM_Plex_Mono',monospace] text-[9px] uppercase tracking-wide text-[#64746B]">
              {visibleChecks.length} sample checks
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-162.5 border-collapse text-left">
              <thead>
                <tr className="bg-[#F7F7F0] font-['IBM_Plex_Mono',monospace] text-[9px] uppercase text-[#64746B]">
                  <th className="py-2 pl-2 font-medium">Product / Finding</th>
                  <th className="px-2 py-2 font-medium">Date · 2026</th>
                  <th className="px-2 py-2 font-medium">Verdict</th>
                  <th className="px-2 py-2 font-medium">Trust /100</th>
                  <th className="w-8 py-2" aria-label="Details" />
                </tr>
              </thead>
              <tbody>
                {visibleChecks.map((check) => (
                  <tr key={check.id} className="border-b border-[#E7EBE4] last:border-0">
                    <td className="py-2 pl-2 pr-3">
                      <div className="flex items-center gap-2">
                        <ProductIcon type={check.icon} />
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold">{check.product}</p>
                          <p className="mt-0.5 truncate text-[10px] text-[#64746B]">{check.finding}</p>
                        </div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-[11px] text-[#64746B]">{check.date}</td>
                    <td className="px-2 py-2"><VerdictBadge verdict={check.verdict} /></td>
                    <td className="px-2 py-2 text-xs font-medium">{check.trust}</td>
                    <td className="px-2 py-2">
                      <a href="/scan" aria-label={`View ${check.product} check`} className="text-[#18543F] hover:text-[#123E30]">
                        <ChevronRight size={15} />
                      </a>
                    </td>
                  </tr>
                ))}
                {visibleChecks.length === 0 && (
                  <tr>
                    <td colSpan="5" className="py-8 text-center text-xs text-[#64746B]">
                      No checks match your search and filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <p id="dashboard-disclaimer" className="mt-3 flex items-start gap-1.5 text-[10px] leading-relaxed text-[#64746B]">
            <Info size={11} className="mt-px shrink-0" />
            All metrics, products, dates and findings are sample data. Results are evidence-based guidance, not a guarantee of contents or safety.
          </p>
        </section>
      </main>
    </div>
  );
}