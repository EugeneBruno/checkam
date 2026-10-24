import { useEffect, useState } from "react";
import {
  AlertTriangle as IconAlertTriangle,
  ArrowUpRight,
  Camera as IconCamera,
  CircleCheck,
  Eye as IconEye,
  FileSearch as IconFileSearch,
  History as IconHistory,
  MessagesSquare as IconMessages,
  Play,
  Scan,
  SpellCheck as IconTextSpellcheck,
  Smartphone as IconPhone,
  Video as IconVideo,
  Bot,
  Terminal,
  Sparkles,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";
import CheckingPage from "./pages/CheckingPage.jsx";
import ResultPage from "./pages/ResultPage.jsx";
import ScanPage from "./pages/ScanPage.jsx";
import DemoPresetToolbar from "./components/scan/DemoPresetToolbar.jsx";
import checkAmLogo from "./public/Check_Am_Logo-removebg-preview.png";
import { setPendingFiles } from "./api.js";
import BrandLoader from "./components/brand/BrandLoader.jsx";
import heroImage from "./public/hero-market.jpg";
import pharmacyImage from "./public/pharmacy.jpg";
import medicinesImage from "./public/medicines.jpg";
import atHomeImage from "./public/at-home.jpg";
import phonesImage from "./public/phones.jpg";
import communityImage from "./public/community.jpg";

const INFO_IMAGES = {
  how: { src: atHomeImage, alt: "A man at home checking a bottle against his phone" },
  check: { src: pharmacyImage, alt: "A pharmacist talking to a customer at the counter" },
  ai: { src: communityImage, alt: "Shoppers looking at a phone together outside a supermarket" },
};

const industries = [
  { image: medicinesImage, title: "Medicines", body: "Matched against 8,910 NAFDAC registrations, NAFDAC counterfeit alerts and batch history." },
  { image: atHomeImage, title: "Food, drinks & cosmetics", body: "NAFDAC number, barcode owner and expiry checks, with online research when it's not in our data." },
  { image: phonesImage, title: "Phones & electronics", body: "IMEI on the box against the phone, NCC device status, and SON certification for electricals." },
];


const checkAm = "Checkam";
const navLinks = ["How it works", "What we check", "For AI assistants", "Sign In",];
const INFO_PAGES = {
  "/how-it-works": "how",
  "/what-we-check": "check",
  "/for-ai-assistants": "ai",
};
const INFO_PATHS = { how: "/how-it-works", check: "/what-we-check", ai: "/for-ai-assistants" };
const INFO_INTRO = {
  how: {
    kicker: "How it works",
    title: "From a photo to a clear answer in seconds.",
    body: "Take a photo or type what you can read. Check Am reads the pack, checks it against regulator data and other buyers’ scans, and researches online only when it has to.",
  },
  check: {
    kicker: "What we check",
    title: "Every check, with its source.",
    body: "Registry numbers, alerts, batch history, barcodes, dates, IMEIs and SON marks. Each result tells you what was checked, against what, and what it can’t prove.",
  },
  ai: {
    kicker: "For AI assistants",
    title: "Check Am inside the assistants people already use.",
    body: "Shopping and chat assistants can call Check Am through MCP, so a buyer can ask whether a product is genuine and get the same evidence-based answer, with sources.",
  },
};
const sources = [
  "8,910 NAFDAC registrations",
  "11,646 SON-certified products",
  "NAFDAC counterfeit alerts",
  "NCC phone checks",
];
function readSavedScan(scanId) {
  if (!scanId) return null;
  const saved = window.sessionStorage.getItem(`checkam:scan:${scanId}`);
  return saved ? JSON.parse(saved) : null;
}

function initialNavigation() {
  const path = window.location.pathname;
  const resultId = path.match(/^\/result\/([^/]+)$/)?.[1];
  const scanId =
    resultId ||
    window.history.state?.scanId ||
    window.sessionStorage.getItem("checkam:active-scan-id");
  const savedScan = readSavedScan(scanId);

  if (resultId && savedScan) {
    return { page: "result", result: savedScan, intake: savedScan.intake, scanId };
  }
  if (path === "/checking" && savedScan) {
    return { page: "checking", result: null, intake: savedScan.intake, scanId };
  }
  if (path === "/scan" || window.history.state?.screen === "intake") {
    return { page: "intake", result: null, intake: null, scanId: null };
  }
  if (INFO_PAGES[path]) {
    return { page: "home", view: INFO_PAGES[path], result: null, intake: null, scanId: null };
  }
  return { page: "home", view: "home", result: null, intake: null, scanId: null };
}



const methods = [
  {
    icon: IconCamera,
    title: "A photo is a good start.",
    body: "Capture the front, then add the registration number and batch panel. One or more photos work.",
    label: "Take photo",
  },
  {
    icon: IconVideo,
    title: "Turn the pack. We’ll read it.",
    body: "Record a 5–15 second video. Frames are compressed on your phone to be kinder to slow data.",
    label: "Record video",
  },
  {
    icon: IconPhone,
    title: "No camera? Type it in.",
    body: "Enter a product name, barcode, NAFDAC number, serial or QR details. Add only what you have.",
    label: "Type details",
  },
];

const checks = [
  {
    icon: IconFileSearch,
    title: "Does the number fit the product?",
    body: "Compare the product name, maker and variant with a public registry snapshot. A valid-looking number alone is not enough.",
  },
  {
    icon: IconTextSpellcheck,
    title: "Do the small details add up?",
    body: "Read label claims, spelling and dates. Check barcode check digits and look for implausible batch or expiry information.",
  },
  {
    icon: IconEye,
    title: "Does the packaging look right?",
    body: "Compare print, logos and packaging with reference images. Visual checks are useful signals, not proof of contents.",
  },
  {
    icon: IconHistory,
    title: "Has this identity appeared before?",
    body: "Look for repeated serials and conflicting batch or expiry details. Explain the history behind a possible clone.",
  },
  {
    icon: IconAlertTriangle,
    title: "Are there public safety alerts?",
    body: "Check available public NAFDAC counterfeit alerts. Show the source and what was checked, not an implied endorsement.",
  },
  {
    icon: IconMessages,
    title: "What have other buyers seen?",
    body: "Surface reports tied to the same product or batch. Buyer observations remain separate from confirmed findings.",
  },
];

const agentSteps = [
  { title: "Checking NAFDAC's online Greenbook", detail: "Is this registration number listed, and for which product?", status: "complete" },
  { title: "Reading counterfeit alerts", detail: "NAFDAC public alerts that name this product or batch", status: "complete" },
  { title: "Finding the official product", detail: "Brand pages and trusted retailers: how the genuine pack looks", status: "active" },
  { title: "Building a reference with sources", detail: "Saved, so the next scan of this product is instant", status: "pending" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("before");
  const [navigation, setNavigation] = useState(initialNavigation);
  const { page, result, intake, scanId } = navigation;
  const view = navigation.view || "home";
  const show = (...views) => views.includes(view);
  const [menuOpen, setMenuOpen] = useState(false);
  // Short Check Am loading screen between pages
  const [pageLoading, setPageLoading] = useState("");
  function showPageLoader(label) {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    setPageLoading(label);
    window.setTimeout(() => setPageLoading(""), 450);
  }

  // Fade sections and cards in as they scroll into view (home page only)
  useEffect(() => {
    if (page !== "home") return undefined;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const targets = document.querySelectorAll(
      "#home-root > section:not(.hero-section) > div, #home-root > section:not(.hero-section) > p, #home-root article, #home-root .grid > div",
    );
    if (reduce || !("IntersectionObserver" in window)) return undefined;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("reveal-in");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    targets.forEach((el) => {
      const siblings = el.parentElement ? [...el.parentElement.children] : [];
      el.style.setProperty("--reveal-delay", `${Math.min(siblings.indexOf(el), 5) * 70}ms`);
      el.classList.add("reveal");
      observer.observe(el);
    });
    return () => observer.disconnect();
  }, [page, view]);

  useEffect(() => {
    function restoreHistoryState(event) {
      const path = window.location.pathname;
      const resultId = path.match(/^\/result\/([^/]+)$/)?.[1];
      const activeScanId = resultId || event.state?.scanId;
      const savedScan = readSavedScan(activeScanId);

      if (resultId && savedScan) {
        setNavigation({
          page: "result",
          result: savedScan,
          intake: savedScan.intake,
          scanId: resultId,
        });
      } else if (
        path === "/checking" &&
        (event.state?.intake || savedScan?.intake)
      ) {
        setNavigation({
          page: "checking",
          result: null,
          intake: event.state?.intake || savedScan.intake,
          scanId: activeScanId,
        });
      } else if (
        path === "/scan" ||
        event.state?.screen === "intake"
      ) {
        setNavigation({ page: "intake", result: null, intake: null, scanId: null });
      } else {
        setNavigation({ page: "home", view: INFO_PAGES[path] || "home", result: null, intake: null, scanId: null });
      }
    }

    window.addEventListener("popstate", restoreHistoryState);
    return () => window.removeEventListener("popstate", restoreHistoryState);
  }, []);

  function navigateToChecking(nextIntakeWithFiles) {
    window.scrollTo(0, 0);
    const id = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const { files, ...nextIntake } = nextIntakeWithFiles;
    setPendingFiles(id, files);
    const scanIntake = { ...nextIntake, id };
    const savedScan = {
      scanId: id,
      intake: scanIntake,
      createdAt: new Date().toISOString(),
    };
    window.sessionStorage.setItem(`checkam:scan:${id}`, JSON.stringify(savedScan));
    window.sessionStorage.setItem("checkam:active-scan-id", id);
    const returnToScan = page === "intake";
    window.history.pushState(
      { screen: "checking", intake: scanIntake, scanId: id, returnToScan },
      "",
      "/checking",
    );
    setNavigation({ page: "checking", result: null, intake: scanIntake, scanId: id });
  }

  function navigateToResult(completedRun) {
    window.scrollTo(0, 0);
    const completedResult = {
      ...completedRun,
      completedAt: new Date().toISOString(),
    };
    window.sessionStorage.setItem(
      `checkam:scan:${completedRun.scanId}`,
      JSON.stringify(completedResult),
    );
    window.history.pushState(
      { screen: "result", scanId: completedRun.scanId },
      "",
      `/result/${encodeURIComponent(completedRun.scanId)}`,
    );
    setNavigation({
      page: "result",
      result: completedResult,
      intake: completedRun.intake,
      scanId: completedRun.scanId,
    });
  }

  function navigateToIntake(prefill = null) {
    window.scrollTo(0, 0);
    showPageLoader("New check");
    window.history.pushState({ screen: "intake" }, "", "/scan");
    setNavigation({ page: "intake", result: null, intake: null, scanId: null, prefill });
  }

  function navigateHome() {
    showPageLoader("Home");
    window.history.pushState({ screen: "home" }, "", "/");
    setNavigation({ page: "home", view: "home", result: null, intake: null, scanId: null });
    window.scrollTo(0, 0);
  }

  function navigateInfo(nextView) {
    showPageLoader({ how: "How it works", check: "What we check", ai: "For AI assistants" }[nextView] || "Loading");
    window.history.pushState({ screen: "home" }, "", INFO_PATHS[nextView] || "/");
    setNavigation({ page: "home", view: nextView, result: null, intake: null, scanId: null });
    setMenuOpen(false);
    window.scrollTo(0, 0);
  }

  // A link that switches page without reloading
  function pageLink(target) {
    const href = target === "home" ? "/" : INFO_PATHS[target];
    return {
      href,
      onClick: (event) => {
        event.preventDefault();
        if (target === "home") navigateHome();
        else navigateInfo(target);
      },
    };
  }

  function navigateBackFromChecking() {
    const returnToScan = Boolean(window.history.state?.returnToScan);
    window.history.pushState(
      { screen: returnToScan ? "intake" : "home" },
      "",
      returnToScan ? "/scan" : "/",
    );
    setNavigation({
      view: "home",
      page: returnToScan ? "intake" : "home",
      result: null,
      intake: null,
      scanId: null,
    });
  }

  return (
    <>
    {page === "intake" && (
      <ScanPage
        key={navigation.prefill ? JSON.stringify(navigation.prefill) : "new"}
        isActive
        onBack={navigateHome}
        onStartResearch={navigateToChecking}
        initialProduct={navigation.prefill || null}
      />
    )}
    {page === "home" && (
    <div id="home-root" className="flex min-h-screen w-full flex-col bg-[#F7F7F0] font-['DM_Sans',sans-serif] text-[#203C32]">
      {/* ─── HEADER ─── */}
      <header className="flex min-h-26 flex-wrap items-center justify-between gap-3 border-b border-[#DCE2D8] px-5 py-3 md:flex-nowrap md:px-4 md:py-0 lg:px-20">
        <a href="/" className="flex items-center gap-2.25">
          <span className="relative h-9 w-36 overflow-hidden" aria-hidden="true">
            <img
              src={checkAmLogo}
              alt="CheckAm Logo"
              className="absolute left-0 -top-7 h-auto w-40 max-w-none"
            />
          </span>
          <span className="sr-only">{checkAm}</span>
        </a>
        <nav className="hidden items-center gap-6 md:flex lg:gap-8" aria-label="Main">
          {[["how", "How it works"], ["check", "What we check"], ["ai", "For AI assistants"]].map(([target, label]) => (
            <a
              key={target}
              {...pageLink(target)}
              aria-current={view === target ? "page" : undefined}
              className={`text-sm font-medium transition-colors hover:text-[#18543F] ${view === target ? "text-[#18543F] underline underline-offset-8 decoration-2" : "text-[#203C32]"}`}
            >
              {label}
            </a>
          ))}
          <a href="/login" className="text-sm font-medium text-[#203C32] transition-colors hover:text-[#18543F]">Sign in</a>
          <a
            href="/scan"
            onClick={(event) => {
              event.preventDefault();
              navigateToIntake();
            }}
            className="flex h-12 items-center justify-center gap-2 rounded-lg border border-[#18543F] bg-[#18543F] px-5 text-center text-[15px] text-white hover:bg-[#123E30] transition-colors"
          >
            <ArrowUpRight size={19} stroke={1.7} className="shrink-0" />
            Start a check
          </a>
        </nav>
        <div className="flex items-center gap-2 md:hidden">
          <a
            href="/scan"
            onClick={(event) => {
              event.preventDefault();
              navigateToIntake();
            }}
            className="flex h-10 items-center justify-center rounded-lg bg-[#18543F] px-4 text-sm font-semibold text-white"
          >
            Start a check
          </a>
          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="flex h-10 w-10 flex-col items-center justify-center gap-1.25 rounded-lg border border-[#DCE2D8] bg-white"
          >
            <span className={`block h-0.5 w-5 bg-[#123E30] transition-transform ${menuOpen ? "translate-y-1.75 rotate-45" : ""}`} />
            <span className={`block h-0.5 w-5 bg-[#123E30] transition-opacity ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block h-0.5 w-5 bg-[#123E30] transition-transform ${menuOpen ? "-translate-y-1.75 -rotate-45" : ""}`} />
          </button>
        </div>
        {menuOpen && (
          <nav className="mobile-menu flex w-full flex-col border-t border-[#DCE2D8] py-2 md:hidden" aria-label="Main">
            {[["home", "Home"], ["how", "How it works"], ["check", "What we check"], ["ai", "For AI assistants"]].map(([target, label]) => (
              <a key={target} {...pageLink(target)} className={`py-3 text-base font-medium ${view === target ? "text-[#18543F]" : "text-[#203C32]"}`}>{label}</a>
            ))}
            <a href="/login" className="py-3 text-base font-medium text-[#203C32]">Sign in</a>
          </nav>
        )}
      </header>

      {view !== "home" && INFO_INTRO[view] && (
        <section className="info-intro grid grid-cols-1 items-center gap-10 border-b border-[#DCE2D8] px-5 py-14 md:px-10 lg:grid-cols-2 lg:gap-16 lg:px-20 lg:py-20">
          <div className="hero-copy">
            <nav className="mb-6 text-sm text-[#64746B]" aria-label="Breadcrumb">
              <a {...pageLink("home")} className="hover:text-[#18543F]">Home</a>
              <span className="mx-2">/</span>
              <span className="text-[#18543F]">{INFO_INTRO[view].kicker}</span>
            </nav>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-[#123E30] md:text-5xl">{INFO_INTRO[view].title}</h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-[#4E6258] md:text-lg">{INFO_INTRO[view].body}</p>
          </div>
          <div className="hero-media">
            <img
              src={INFO_IMAGES[view].src}
              alt={INFO_IMAGES[view].alt}
              className="h-64 w-full rounded-3xl object-cover md:h-80 lg:h-96"
            />
          </div>
        </section>
      )}

      {/* ─── HERO SECTION ─── */}
      {show("home") && (
      <section className="hero-section flex flex-col items-center gap-12 px-5 py-12 md:px-10 lg:flex-row lg:gap-20 lg:px-20 lg:pb-19 lg:pt-17">
        <div className="hero-copy flex w-full flex-col items-start gap-7 lg:w-155 lg:shrink-0">
          <p className="text-sm font-semibold text-[#18543F]">
            For buyers in Nigeria
          </p>
          <h1 className="text-[44px] font-semibold leading-[1.07] text-[#123E30] md:text-[56px] xl:text-[66px]">
            Check before you buy. Know more before you use.
          </h1>
          <div className="flex w-full max-w-135 flex-col gap-4">
            <p className="text-xl leading-normal">
              A clearer picture of the products in your hands. Check packaging,
              public records and product history — before you decide.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="/scan"
                onClick={(event) => {
                  event.preventDefault();
                  navigateToIntake();
                }}
                className="flex h-13 items-center justify-center gap-3 rounded-lg border border-[#18543F] bg-[#18543F] px-5 text-center text-[15px] text-white hover:bg-[#123E30] transition-colors"
              >
                <Scan size={19} stroke={1.7} className="shrink-0 items-center justify-center pr-8" />
                Start a check
              </a>
              <a
                {...pageLink("how")}
                className="flex h-13 items-center justify-center gap-3 rounded-lg border border-[#DCE2D8] bg-white px-5 text-center text-[15px] text-[#18543F] hover:bg-slate-50 transition-colors"
              >
                <Play size={19} stroke={1.7} className="shrink-0" />
                See how it works
              </a>
            </div>
            <p className="text-[13px] leading-normal text-[#64746B]">
              Free for consumers. No account needed for your first check.
            </p>
          </div>
        </div>

        <div className="hero-media relative w-full max-w-145 pb-6 lg:h-143.5 lg:flex-1 lg:pb-0">
          <img
            src={heroImage}
            alt="A shopper in a Lagos market checking a medicine box with her phone"
            className="aspect-580/574 h-full w-full rounded-3xl object-cover object-[62%_center]"
          />
          <div className="absolute left-6 top-5.5 flex items-center gap-1.75 rounded-full bg-[#F7F7F0] px-3 py-2 text-xs font-semibold text-[#18543F] shadow-sm">
            <Scan size={15} stroke={1.7} />
            More clarity, right at the shelf.
          </div>
          <div className="absolute inset-x-4 bottom-0 flex w-auto max-w-87.5 flex-col gap-4 rounded-2xl border border-[#DCE2D8] bg-white p-6 shadow-[0_12px_40px_rgba(20,61,48,0.08)] sm:inset-x-auto sm:-left-7 sm:w-87.5 lg:bottom-6">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 rounded-full bg-[#E8F0E8] px-2.5 py-1.5 text-xs text-[#18543F] font-semibold">
                <CircleCheck size={14} stroke={1.7} />
                Likely genuine
              </span>
              <span className="font-['IBM_Plex_Mono',monospace] text-[10px] text-[#64746B]">
                EXAMPLE
              </span>
            </div>
            <div className="text-[21px] font-semibold text-[#123E30]">Example result</div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-[40px] font-semibold text-[#18543F]">84</span>
              <span className="text-xs text-[#64746B]">/100 · medium confidence</span>
            </div>
            <div className="flex items-center gap-2.25 text-[13px] text-[#203C32]">
              <CircleCheck size={16} stroke={1.7} color="#18543F" />
              Label matches public registry snapshot
            </div>
            <p className="text-xs leading-normal text-[#64746B]">
              A useful signal, not a guarantee. Contents have not been tested.
            </p>
          </div>
        </div>
      </section>
      )}

      {/* ─── EVIDENCE RIBBON ─── */}
      {show("home", "check") && (
      <section className="flex flex-col gap-3 bg-[#E8F0E8] px-5 py-6 md:px-10 lg:flex-row lg:items-center lg:justify-between lg:px-20">
        <p className="text-sm font-semibold text-[#18543F]">
          Checked against real regulator data
        </p>
        {sources.map((source) => (
          <span key={source} className="flex items-center gap-2 text-[13px] text-[#18543F] font-medium">
            <CircleCheck size={14} stroke={1.7} />
            {source}
          </span>
        ))}
      </section>
      )}

      {/* ─── SECTION 1: HOW CHECKS WORK ─── */}
      {show("how", "check") && (
      <section id="how-it-works" className="px-5 py-16 md:px-10 lg:px-20 lg:py-24 border-b border-[#DCE2D8]">
        {show("how") && (<>
        <div className="max-w-2xl mb-14">
          <p className="text-sm font-semibold text-[#18543F] mb-3">
            Three ways in
          </p>
          <h2 className="text-3xl md:text-4xl lg:text-[42px] font-semibold text-[#123E30] leading-tight mb-4">
            Start with whatever you have in hand.
          </h2>
          <p className="text-base md:text-lg text-[#4E6258] leading-relaxed">
            A registration number can be copied onto a package, so we compare it with other available evidence, including packaging details, product history, and public records.
          </p>
        </div>

        {/* 3 Capture Methods */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          {methods.map((method, idx) => {
            const Icon = method.icon;
            return (
              <div
                key={idx}
                className="flex flex-col justify-between rounded-2xl border border-[#DCE2D8] bg-white p-7 shadow-sm hover:shadow-md transition-shadow"
              >
                <div>
                  <h3 className="flex items-center gap-3 text-xl font-semibold text-[#123E30] mb-2.5">
                    <Icon size={24} strokeWidth={1.8} className="shrink-0 text-[#18543F]" />
                    {method.title}
                  </h3>
                  <p className="text-sm text-[#4E6258] leading-relaxed mb-6">
                    {method.body}
                  </p>
                </div>
                <a
                  href="/scan"
                  onClick={(event) => {
                    event.preventDefault();
                    navigateToIntake();
                  }}
                  className="inline-flex items-center justify-center gap-2 text-center text-sm font-semibold text-[#18543F] hover:text-[#123E30] transition-colors"
                >
                  <span>{method.label}</span>
                  <ChevronRight size={16} />
                </a>
              </div>
            );
          })}
        </div>

        </>)}

        {/* What We Check Grid */}
        {show("check") && (
        <div
          id="what-we-check"
          className="rounded-3xl bg-[#18543F] p-6 md:p-8"
        >
          <div className="max-w-xl mb-10">
            <h3 className="text-2xl font-semibold text-[#FFFDEF] mb-2">
              What every check covers
            </h3>
            <p className="text-sm text-[#FFFDEF]">
              The same checks run for every product to keep results consistent and explainable.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {checks.map((chk, idx) => {
              const Icon = chk.icon;
              return (
                <div
                  key={idx}
                  className="rounded-2xl border border-white/20 bg-[#18543F] p-6 flex flex-col gap-3"
                >
                  <Icon
                    size={20}
                    strokeWidth={1.5}
                    className="text-[#BCD0C1]"
                    aria-hidden="true"
                  />
                  <h4 className="text-base font-semibold text-white">
                    {chk.title}
                  </h4>
                  <p className="text-xs md:text-sm text-white/85 leading-relaxed">
                    {chk.body}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
        )}
      </section>
      )}

      {/* ─── WHAT WE CHECK, BY PRODUCT TYPE ─── */}
      {show("home", "check") && (
      <section className="px-5 py-16 md:px-10 lg:px-20 lg:py-24 border-b border-[#DCE2D8]">
        <div className="max-w-2xl mb-10">
          <p className="text-sm font-semibold text-[#18543F] mb-3">Built for what gets faked most</p>
          <h2 className="text-3xl md:text-4xl font-semibold text-[#123E30] leading-tight">
            One app for the things people buy every day.
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {industries.map((item) => (
            <article key={item.title} className="overflow-hidden rounded-2xl border border-[#DCE2D8] bg-white">
              <img src={item.image} alt={item.title} loading="lazy" className="aspect-4/3 w-full object-cover" />
              <div className="p-6">
                <h3 className="text-lg font-semibold text-[#123E30] mb-2">{item.title}</h3>
                <p className="text-sm text-[#4E6258] leading-relaxed">{item.body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      )}

      {/* ─── MORE ABOUT CHECK AM (home only) ─── */}
      {show("home") && (
      <section className="px-5 py-16 md:px-10 lg:px-20 lg:py-20 border-b border-[#DCE2D8] bg-[#F3F5EE]">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {[
            ["how", "How it works", "Photo, video or typed details: what happens after you press Check."],
            ["check", "What we check", "Registry numbers, alerts, batch history, barcodes, IMEIs and SON marks."],
            ["ai", "For AI assistants", "Check Am inside the shopping and chat assistants people already use."],
          ].map(([target, title, body]) => (
            <a key={target} {...pageLink(target)} className="group rounded-2xl border border-[#DCE2D8] bg-white p-7 transition-shadow hover:shadow-md">
              <h3 className="mb-2 flex items-center justify-between text-lg font-semibold text-[#123E30]">
                {title}
                <ChevronRight size={18} className="transition-transform group-hover:translate-x-1" />
              </h3>
              <p className="text-sm leading-relaxed text-[#4E6258]">{body}</p>
            </a>
          ))}
        </div>
      </section>
      )}

      {/* ─── SECTION 2: GUIDANCE, RESEARCH & COMMUNITY ─── */}
      {show("how") && (
      <section className="px-5 py-16 md:px-10 lg:px-20 lg:py-24 border-b border-[#DCE2D8] bg-[#F3F5EE]">
        {/* Sub-part A: Contextual Advice */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center mb-24">
          <div className="lg:col-span-5 space-y-5">
            <p className="text-sm font-semibold text-[#18543F]">
              Before or after you buy
            </p>
            <h2 className="text-3xl md:text-4xl font-semibold text-[#123E30] leading-tight">
              Guidance tailored to where you stand.
            </h2>
            <p className="text-sm md:text-base text-[#4E6258] leading-relaxed">
              Checking an item at a market stall calls for different guidance than inspecting a pack at home. Switch scenarios to see how the recommendation changes.
            </p>

            {/* Posture Toggle */}
            <div className="inline-flex rounded-xl border border-[#DCE2D8] bg-white p-1 gap-1">
              <button
                onClick={() => setActiveTab("before")}
                className={`inline-flex items-center justify-center text-center px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === "before"
                    ? "bg-[#18543F] text-white shadow-sm"
                    : "text-[#4E6258] hover:text-[#123E30]"
                }`}
              >
                Before buying
              </button>
              <button
                onClick={() => setActiveTab("already")}
                className={`inline-flex items-center justify-center text-center px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === "already"
                    ? "bg-[#18543F] text-white shadow-sm"
                    : "text-[#4E6258] hover:text-[#123E30]"
                }`}
              >
                Already bought
              </button>
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-3xl border border-[#DCE2D8] bg-white p-6 md:p-8 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-[#DCE2D8] pb-4">
                <span className="text-xs font-['IBM_Plex_Mono',monospace] text-[#64746B] uppercase">
                  Scenario: {activeTab === "before" ? "At Pharmacy Shelf" : "Home Pantry Inspection"}
                </span>
                <span className="text-xs px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 font-medium border border-rose-200">
                  Suspicious Batch Flagged
                </span>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs uppercase font-bold text-[#64746B] tracking-wider">
                  Resulting Recommendation
                </h4>
                {activeTab === "before" ? (
                  <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm leading-relaxed">
                    <strong>Advisory: Don’t buy.</strong> The registration matches an active record, but this demo batch was reported elsewhere with an earlier expiry date. Ask the vendor for a different batch and verify it independently.
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-sm leading-relaxed">
                    <strong>Advisory: Do not consume.</strong> Set this pack aside and contact a pharmacist or the relevant regulator for guidance. You can also report the details to help inform other buyers.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sub-part B: The Research Agent */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center mb-24">
          <div className="lg:col-span-6 order-2 lg:order-1">
            <div className="rounded-3xl border border-[#203C32] bg-[#122E24] text-white p-6 md:p-8 font-['IBM_Plex_Mono',monospace] shadow-xl">
              <div className="flex items-center justify-between border-b border-[#254A3B] pb-4 mb-5">
                <div className="flex items-center gap-2 text-xs text-[#8BE4C1]">
                  <Terminal size={15} />
                  <span>Product research in progress</span>
                </div>
                <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>

              <div className="space-y-4 text-xs">
                {agentSteps.map((step, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <span className="mt-0.5">
                      {step.status === "complete" ? (
                        <CheckCircle2 size={15} className="text-emerald-400" />
                      ) : step.status === "active" ? (
                        <Sparkles size={15} className="text-amber-300 animate-spin" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />
                      )}
                    </span>
                    <div>
                      <p className={step.status === "pending" ? "text-slate-400" : "text-white font-medium"}>
                        {step.title}
                      </p>
                      <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                        {step.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-4 border-t border-[#254A3B] text-[11px] text-slate-400 flex items-center justify-between">
                <span>Every finding has a source</span>
                <span className="text-emerald-400">Saved for the next buyer</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 order-1 lg:order-2 space-y-4">
            <p className="text-sm font-semibold text-[#18543F]">
              Products we don’t have yet
            </p>
            <h2 className="text-3xl md:text-4xl font-semibold text-[#123E30] leading-tight">
              When it’s not in our data, we look it up.
            </h2>
            <p className="text-sm md:text-base text-[#4E6258] leading-relaxed">
              Check Am searches NAFDAC’s online Greenbook first, then official brand pages and counterfeit alerts. Every finding comes with its source, and is saved so the next buyer gets an instant answer.
            </p>
          </div>
        </div>

        {/* Sub-part C: Community Memory & Reporting */}
        <div className="overflow-hidden rounded-3xl border border-[#DCE2D8] bg-white">
          <img src={communityImage} alt="Shoppers outside a supermarket looking at a phone together" loading="lazy" className="h-64 w-full object-cover object-[50%_20%] md:h-96" />
          <div className="p-8 md:p-12">
          <div className="max-w-2xl mb-8">
            <p className="text-sm font-semibold text-[#18543F] mb-2">
              Buyer reports
            </p>
            <h3 className="text-2xl md:text-3xl font-semibold text-[#123E30]">
              Every report protects the next buyer.
            </h3>
            <p className="text-sm text-[#4E6258] mt-2">
              A buyer can report a suspicious batch and include the details they observed. Reports remain attributed to the batch and clearly distinguished from confirmed findings.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-5 rounded-2xl bg-[#F7F7F0] border border-[#DCE2D8]">
              <div className="text-2xl font-bold text-[#18543F] mb-1">Kept separate</div>
              <div className="text-xs font-bold text-[#123E30] mb-1">Reports are not findings</div>
              <p className="text-xs text-[#4E6258]">
                Community reports stay distinct from verified findings and should be reviewed before action is taken.
              </p>
            </div>
            <div className="p-5 rounded-2xl bg-[#F7F7F0] border border-[#DCE2D8]">
              <div className="text-2xl font-bold text-[#18543F] mb-1">Batch history</div>
              <div className="text-xs font-bold text-[#123E30] mb-1">Copied batch numbers show up</div>
              <p className="text-xs text-[#4E6258]">
                Repeated serial numbers reported in different locations can be surfaced for further review.
              </p>
            </div>
            <div className="p-5 rounded-2xl bg-[#F7F7F0] border border-[#DCE2D8]">
              <div className="text-2xl font-bold text-[#18543F] mb-1">Shareable</div>
              <div className="text-xs font-bold text-[#123E30] mb-1">Ready for NAFDAC</div>
              <p className="text-xs text-[#4E6258]">
                Reports can help consumers prepare clear information to share with regulators or consumer protection agencies.
              </p>
            </div>
          </div>
        </div>
        </div>
      </section>
      )}

      {/* ─── SECTION 3: AI ASSISTANT SUPPORT ─── */}
      {show("ai") && (
      <section id="for-ai-assistants" className="px-5 py-16 md:px-10 lg:px-20 lg:py-24 border-b border-[#DCE2D8] bg-[#122E24] text-white">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <Bot size={15} />
              Help for shopping assistants
            </div>
            <h2 className="text-3xl md:text-5xl font-semibold leading-tight text-white">
              A clearer answer before you buy.
            </h2>
            <p className="text-slate-300 text-base md:text-lg leading-relaxed">
              Shopping assistants can use Check Am to review product details, compare them with available public records, and explain anything that does not seem to match.
            </p>
            <div className="space-y-3 text-sm text-slate-200">
              <p>Share product details and a photo.</p>
              <p>Check available records and buyer reports.</p>
              <p>Get a clear summary of what matched and what needs a closer look.</p>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="rounded-2xl border border-[#254A3B] bg-[#0C1F18] p-6 md:p-8 space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase text-emerald-300">Example check</p>
                <h3 className="mt-2 text-xl font-semibold text-white">The details do not match</h3>
              </div>
              <p className="text-sm leading-relaxed text-slate-300">
                The registration number appears to belong to a different medicine than the one shown. Ask a pharmacist or the seller to clarify before buying.
              </p>
              <div className="border-t border-[#254A3B] pt-4 text-xs leading-relaxed text-slate-400">
                A Check Am result is a helpful signal, not proof that a product is genuine or safe.
              </div>
            </div>
          </div>
        </div>
      </section>
      )}

      {/* ─── SECTION 4: TRUST, LIMITS & DEMO PRESETS ─── */}
      <section className="px-5 pb-0 pt-16 md:px-10 lg:px-20 lg:pb-0 lg:pt-24">
        {show("check") && (<>
        <div className="max-w-2xl mb-12">
          <p className="text-sm font-semibold text-[#18543F] mb-3">
            What a photo can’t tell you
          </p>
          <h2 className="text-3xl md:text-4xl font-semibold text-[#123E30] mb-4">
            Clear about what a check can’t prove.
          </h2>
          <p className="text-base text-[#4E6258] leading-relaxed">
            A visual check cannot establish that a product is genuine or safe. Photos may reveal inconsistencies, but they cannot replace laboratory testing.
          </p>
        </div>

        {/* Limits Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
          <div className="p-6 rounded-2xl border border-[#DCE2D8] bg-white">
            <h4 className="font-semibold text-[#123E30] mb-2">Visual limit</h4>
            <p className="text-xs text-[#4E6258] leading-relaxed">
              Replicas can closely match external packaging. When visual evidence is inconclusive, additional photos may help with review.
            </p>
          </div>
          <div className="p-6 rounded-2xl border border-[#DCE2D8] bg-white">
            <h4 className="font-semibold text-[#123E30] mb-2">Internal composition</h4>
            <p className="text-xs text-[#4E6258] leading-relaxed">
              Chemical contents are not assessed by a visual check, so the result should not be treated as clinical or safety assurance.
            </p>
          </div>
          <div className="p-6 rounded-2xl border border-[#DCE2D8] bg-white">
            <h4 className="font-semibold text-[#123E30] mb-2">Independent snapshot</h4>
            <p className="text-xs text-[#4E6258] leading-relaxed">
              Public records and on-pack marks can provide useful context but do not imply regulatory endorsement.
            </p>
          </div>
        </div>

        </>)}

        {/* Closing call to action */}
        <div className="-mx-5 mt-16 flex flex-col items-start justify-between gap-6 bg-[#E8F0E8] px-5 py-10 sm:flex-row sm:items-center md:-mx-10 md:px-10 lg:-mx-20 lg:px-20">
          <div>
            <p className="mb-2 text-sm font-semibold text-[#18543F]">
              A small check, a more informed choice.
            </p>
            <h3 className="text-2xl font-semibold text-[#123E30]">
              What’s in your hands?
            </h3>
            <p className="mt-2 text-sm text-[#64746B]">
              Start with a photo. We’ll help you understand the evidence.
            </p>
          </div>
          <div className="shrink-0">
            <a
              href="/scan"
              onClick={(event) => {
                event.preventDefault();
                navigateToIntake();
              }}
              className="flex h-12 items-center justify-center gap-2 rounded-lg bg-[#18543F] px-6 text-center text-sm font-semibold text-white transition-colors hover:bg-[#123E30]"
            >
              <Scan size={16} className="shrink-0" />
              Start a check
            </a>
            <p className="mt-2 text-[10px] text-[#64746B]">
              Free to use. No sign-up required.
            </p>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="bg-[#123E30] px-5 py-10 text-xs text-[#BCD0C1] md:px-10 lg:px-20">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-5 md:gap-10">
          <div className="col-span-2 space-y-4 md:col-span-2">
            <div className="flex items-center gap-2">
              <span className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-md bg-[#F7F7F0]">
                <img
                  src={checkAmLogo}
                  alt="CheckAm"
                  className="h-12 w-full object-contain"
                />
              </span>
              <span className="text-sm font-semibold text-white">Check Am</span>
            </div>
            <p className="max-w-sm leading-relaxed">
              Evidence-based product checking for people in Nigeria and their AI assistants.
            </p>
            <p className="max-w-sm text-[10px] leading-relaxed text-[#8DA99A]">
              Built by Team Syntax for T.I.C Hackathon 3.0.
            </p>
          </div>

          <nav aria-label="Explore" className="space-y-3">
            <h3 className="font-semibold text-white">Explore</h3>
            <a
              href="/scan"
              onClick={(event) => {
                event.preventDefault();
                navigateToIntake();
              }}
              className="block hover:text-white"
            >
              Start a check
            </a>
            <a {...pageLink("how")} className="block hover:text-white">How it works</a>
            <a {...pageLink("check")} className="block hover:text-white">What we check</a>
          </nav>

          <nav aria-label="Your space" className="space-y-3">
            <h3 className="font-semibold text-white">Your space</h3>
            <a href="/login" className="block hover:text-white">Sign in</a>
            <a href="/login" className="block hover:text-white">Scan history</a>
            <a href="/login" className="block hover:text-white">Your reports</a>
          </nav>

          <nav aria-label="Trust" className="space-y-3">
            <h3 className="font-semibold text-white">Trust</h3>
            <a href="#trust-limits" className="block hover:text-white">Privacy</a>
            <a href="#trust-limits" className="block hover:text-white">Terms &amp; limits</a>
            <a {...pageLink("ai")} className="block hover:text-white">For AI assistants</a>
          </nav>
        </div>

        <div className="mt-8 flex flex-col gap-3 border-t border-white/15 pt-4 text-[10px] text-[#8DA99A] sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Check Am. Data: NAFDAC Greenbook, NAFDAC alerts, SON certified products, NCC Device Checker.</p>
          <p id="trust-limits">
            Informational only. Not a regulator or a safety certification.
          </p>
        </div>
      </footer>
    </div>
    )}
    {page === "checking" && intake && (
      <CheckingPage
        intake={intake}
        scanId={scanId}
        onBack={navigateBackFromChecking}
        onComplete={navigateToResult}
      />
    )}
    {page === "result" && result && (
      <ResultPage
        result={result}
        onBack={navigateHome}
        onScanAgain={(prefill) => navigateToIntake(prefill)}
      />
    )}
    {page !== "result" && <DemoPresetToolbar onSelect={navigateToChecking} />}
    {pageLoading && <BrandLoader variant="overlay" label={pageLoading} />}
    </>
  );
}