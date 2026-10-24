import { useEffect, useState } from 'react'
import CheckingPage from './pages/CheckingPage.jsx'
import ResultPage from './pages/ResultPage.jsx'
import ScanPage from './pages/ScanPage.jsx'
import DemoPresetToolbar from './components/scan/DemoPresetToolbar.jsx'
import viteLogo from './assets/vite.svg'
import './App.css'

function readSavedScan(scanId) {
  
  if (!scanId) return null
  const saved = window.sessionStorage.getItem(`checkam:scan:${scanId}`)
  return saved ? JSON.parse(saved) : null
}

function initialNavigation() {
  const path = window.location.pathname
  const resultId = path.match(/^\/result\/([^/]+)$/)?.[1]
  const scanId = resultId || window.history.state?.scanId || window.sessionStorage.getItem('checkam:active-scan-id')
  const savedScan = readSavedScan(scanId)
  const result = resultId ? savedScan : null

  if (result) return { page: 'result', result, intake: result.intake, scanId }
  if (path === '/checking' && savedScan) return { page: 'checking', result: null, intake: savedScan.intake, scanId }
  if (window.history.state?.screen === 'intake') return { page: 'intake', result: null, intake: null, scanId: null }
  return { page: 'home', result: null, intake: null, scanId: null }
}

const examples = {
  skincare: {
    category: 'SKINCARE · SAMPLE RESULT',
    product: 'Daily Defense SPF 50',
    subtitle: 'Brightwell · 50 ml',
    score: 68,
    confidence: 'Medium',
    verdict: 'Needs a closer look',
    explanation: 'Some details look consistent, but we couldn’t confirm this exact product registration.',
    checks: [
      ['Packaging details', 'Some differences', 'warning'],
      ['Registration number', 'Not confirmed', 'pending'],
      ['Price & seller', 'Review recommended', 'warning'],
    ],
    next: 'Take a clear photo of the registration number',
    color: 'amber',
    productMark: 'b',
  },
  fashion: {
    category: 'FASHION · SAMPLE RESULT',
    product: 'Everyday Court Low',
    subtitle: 'Northline · White / 42',
    score: 42,
    confidence: 'Low',
    verdict: 'Not enough evidence',
    explanation: 'Packaging photos alone can’t confirm authenticity. A label and stitching photo would help.',
    checks: [
      ['Logo & proportions', 'Needs another angle', 'warning'],
      ['Style code', 'Not checked', 'pending'],
      ['Construction details', 'Photo needed', 'pending'],
    ],
    next: 'Photograph the inside size and style tag',
    color: 'slate',
    productMark: 'n',
  },
}

function ArrowIcon({ diagonal = false }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" className="landing-arrow">
      {diagonal
        ? <path d="M5 15 15 5M6 5h9v9" />
        : <path d="M3.5 10h12m-5-5 5 5-5 5" />}
    </svg>
  )
}

function CheckAmMark() {
  return (
    <img className="landing-mark" src={viteLogo} alt="" />
  )
}

function App() {
  const [activeExample, setActiveExample] = useState('skincare')
  const [navigation, setNavigation] = useState(initialNavigation)
  const { page, result, intake, scanId } = navigation
  const sample = examples[activeExample]

  useEffect(() => {
    function restoreHistoryState(event) {
      const path = window.location.pathname
      const resultId = path.match(/^\/result\/([^/]+)$/)?.[1]
      const activeScanId = resultId || event.state?.scanId
      const savedScan = readSavedScan(activeScanId)
      if (resultId && savedScan) {
        setNavigation({ page: 'result', result: savedScan, intake: savedScan.intake, scanId: resultId })
      } else if (path === '/checking' && (event.state?.intake || savedScan?.intake)) {
        setNavigation({
          page: 'checking',
          result: null,
          intake: event.state?.intake || savedScan.intake,
          scanId: activeScanId,
        })
      } else if (event.state?.screen === 'intake') {
        setNavigation({ page: 'intake', result: null, intake: null, scanId: null })
      } else {
        setNavigation({ page: 'home', result: null, intake: null, scanId: null })
      }
    }

    window.addEventListener('popstate', restoreHistoryState)
    return () => window.removeEventListener('popstate', restoreHistoryState)
  }, [])

  function navigateToChecking(nextIntake) {
    const id = window.crypto.randomUUID()
    const scanIntake = { ...nextIntake, id }
    const savedScan = { scanId: id, intake: scanIntake, createdAt: new Date().toISOString() }
    window.sessionStorage.setItem(`checkam:scan:${id}`, JSON.stringify(savedScan))
    window.sessionStorage.setItem('checkam:active-scan-id', id)
    const returnToScan = page === 'intake'
    window.history.pushState({ screen: 'checking', intake: scanIntake, scanId: id, returnToScan }, '', '/checking')
    setNavigation({ page: 'checking', result: null, intake: scanIntake, scanId: id })
  }

  function navigateToResult(completedRun) {
    const completedResult = { ...completedRun, completedAt: new Date().toISOString() }
    window.sessionStorage.setItem(`checkam:scan:${completedRun.scanId}`, JSON.stringify(completedResult))
    window.history.pushState({ screen: 'result', scanId: completedRun.scanId }, '', `/result/${encodeURIComponent(completedRun.scanId)}`)
    setNavigation({
      page: 'result',
      result: completedResult,
      intake: completedRun.intake,
      scanId: completedRun.scanId,
    })
  }

  function navigateToIntake() {
    window.history.pushState({ screen: 'intake' }, '', '/')
    setNavigation({ page: 'intake', result: null, intake: null, scanId: null })
  }

  function navigateHome() {
    window.history.pushState({ screen: 'home' }, '', '/')
    setNavigation({ page: 'home', result: null, intake: null, scanId: null })
  }

  function navigateBackFromChecking() {
    const returnToScan = Boolean(window.history.state?.returnToScan)
    window.history.pushState({ screen: returnToScan ? 'intake' : 'home' }, '', '/')
    setNavigation({
      page: returnToScan ? 'intake' : 'home',
      result: null,
      intake: null,
      scanId: null,
    })
  }

  return (
    <>
    {page === 'intake' && <ScanPage
      isActive
      onBack={navigateHome}
      onStartResearch={navigateToChecking}
    />}
    {page === 'home' && (
    <main className="landing-page" id="top">
      <header className="landing-header">
        <a className="landing-brand" href="#top" aria-label="CheckAm home">
          <CheckAmMark />
          <span>CheckAm<span className="landing-brand-period">.</span></span>
        </a>
        <nav className="landing-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#what-we-check">What we check</a>
          <a href="#sample-report">Sample report</a>
        </nav>
        <a className="landing-nav-cta" href="#sample-report">Explore the demo <ArrowIcon /></a>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="landing-eyebrow"><span /> A clearer way to check what you buy</div>
          <h1>A fake can copy<br />a number. <span>Not a story.</span></h1>
          <p className="landing-lede">
            CheckAm helps you look beyond the label. Bring a photo, compare the details,
            and see what the evidence says—before you buy or after.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-button landing-button-primary" type="button" onClick={navigateToIntake}>Start a product check <ArrowIcon /></button>
            <a className="landing-text-link" href="#how-it-works">See how it works <span>↓</span></a>
          </div>
          <div className="landing-trust-row">
            <span className="landing-trust-icon">✓</span>
            <span>Evidence first</span><i />
            <span>Clear about uncertainty</span><i />
            <span>No purchase bots</span>
          </div>
        </div>

        <div className="landing-hero-visual" aria-label="Example CheckAm product check">
          <div className="landing-orbit landing-orbit-one" />
          <div className="landing-orbit landing-orbit-two" />
          <div className="landing-float-tag landing-float-photo"><span>▧</span> Product photo <i>✓</i></div>
          <div className="landing-float-tag landing-float-match"><span>⌕</span> Details compared</div>
          <div className="landing-product-card">
            <div className="landing-card-top"><span className="landing-card-label">SAMPLE PRODUCT CHECK</span><span className="landing-card-menu">···</span></div>
            <div className="landing-product-stage">
              <div className="landing-product-glow" />
              <div className="landing-bottle">
                <div className="landing-bottle-cap" />
                <div className="landing-bottle-neck" />
                <div className="landing-bottle-body">
                  <span className="landing-bottle-leaf">✳</span>
                  <strong>BRIGHT<br />WELL</strong>
                  
                </div>
              </div>
              <span className="landing-scan-corner corner-one" />
              <span className="landing-scan-corner corner-two" />
              <span className="landing-scan-corner corner-three" />
              <span className="landing-scan-corner corner-four" />
              <div className="landing-scan-line" />
            </div>
            <div className="landing-product-details">
              <div><small>IDENTIFIED PRODUCT</small><strong>Daily Defense SPF 50</strong><span>Brightwell · Skincare</span></div>
              <span className="landing-match-chip">Possible match</span>
            </div>
            <div className="landing-card-divider" />
            <div className="landing-mini-checks">
              <span><i className="mini-check-ok">✓</i> Packaging</span>
              <span><i className="mini-check-warn">!</i> Registration</span>
              <span><i className="mini-check-ok">✓</i> Listing details</span>
            </div>
          </div>
          <div className="landing-float-score"><span className="landing-score-ring">68</span><span><strong>Trust score</strong><small>Evidence-based, not a guarantee</small></span></div>
          <div className="landing-visual-caption"><span>01</span> A more complete picture, one check at a time</div>
        </div>
        <div className="landing-hero-bottom">
          <span>BUILT FOR THE MOMENT BEFORE “ADD TO CART”</span>
          <span className="landing-bottom-line" />
          <span>AND THE MOMENT AFTER</span>
        </div>
      </section>

      <section className="landing-proof-strip" aria-label="Product principles">
        <div><span className="proof-icon">⌕</span><span><strong>Look for patterns</strong><small>Not just one number or label</small></span></div>
        <div><span className="proof-icon">▤</span><span><strong>Show the evidence</strong><small>See what passed—and what didn’t</small></span></div>
        <div><span className="proof-icon">↗</span><span><strong>Know what to do next</strong><small>Get a useful next step, not a guess</small></span></div>
      </section>

      <section className="landing-section landing-how" id="how-it-works">
        <div className="landing-section-intro">
          <div className="landing-eyebrow"><span /> SIMPLE BY DESIGN</div>
          <h2>From “I’m not sure”<br />to <span>better informed.</span></h2>
          <p>No special equipment or expert knowledge needed. Start with what you can see.</p>
        </div>
        <div className="landing-steps">
          <article className="landing-step">
            <span className="landing-step-number">01</span>
            <div className="landing-step-icon landing-step-camera"><span>▧</span><i>+</i></div>
            <h3>Show us the item</h3>
            <p>Add a photo, a short video, or the product and listing details you have.</p>
          </article>
          <article className="landing-step">
            <span className="landing-step-number">02</span>
            <div className="landing-step-icon landing-step-search"><span>⌕</span><i>···</i></div>
            <h3>Check the details</h3>
            <p>Compare packaging, identifiers, references, and seller signals where available.</p>
          </article>
          <article className="landing-step">
            <span className="landing-step-number">03</span>
            <div className="landing-step-icon landing-step-report"><span>▤</span><i>✓</i></div>
            <h3>Decide with context</h3>
            <p>Review a plain-language summary, its evidence, and what still needs checking.</p>
          </article>
        </div>
      </section>

      <section className="landing-checks-section" id="what-we-check">
        <div className="landing-checks-copy">
          <div className="landing-eyebrow"><span /> MORE THAN A BARCODE</div>
          <h2>A consistent story<br />is harder to fake.</h2>
          <p>A single detail can be copied. CheckAm is designed to weigh several signals together and make gaps visible—not hide them.</p>
          <a className="landing-text-link" href="#sample-report">See an example report <ArrowIcon diagonal /></a>
        </div>
        <div className="landing-signal-list">
          <div className="landing-signal">
            <span className="signal-number">01</span>
            <span className="signal-icon">▤</span>
            <span className="signal-copy"><strong>Packaging & print</strong><small>Logo, spelling, layout, and print quality</small></span>
            <span className="signal-arrow">↗</span>
          </div>
          <div className="landing-signal">
            <span className="signal-number">02</span>
            <span className="signal-icon">#</span>
            <span className="signal-copy"><strong>Product identifiers</strong><small>Barcode, batch, registration, or style code</small></span>
            <span className="signal-arrow">↗</span>
          </div>
          <div className="landing-signal">
            <span className="signal-number">03</span>
            <span className="signal-icon">⌕</span>
            <span className="signal-copy"><strong>Listing & seller context</strong><small>Price, seller details, and product history</small></span>
            <span className="signal-arrow">↗</span>
          </div>
          <div className="landing-signal">
            <span className="signal-number">04</span>
            <span className="signal-icon">◌</span>
            <span className="signal-copy"><strong>Visual references</strong><small>Compare with known, genuine product details</small></span>
            <span className="signal-arrow">↗</span>
          </div>
          <p className="landing-signal-note"><span>i</span> What can’t be checked is shown as “not checked”—never quietly treated as a pass.</p>
        </div>
      </section>

      <section className="landing-report-section" id="sample-report">
        <div className="landing-report-intro">
          <div className="landing-eyebrow"><span /> A RESULT SHOULD SHOW ITS WORK</div>
          <h2>Not just a verdict.<br /><span>A reason to trust it.</span></h2>
          <p>Every result should explain what was checked, what wasn’t, and how confident the system is.</p>
          <div className="landing-example-switch" role="group" aria-label="Choose a sample report">
            <button type="button" className={activeExample === 'skincare' ? 'active' : ''} aria-pressed={activeExample === 'skincare'} onClick={() => setActiveExample('skincare')}>Skincare</button>
            <button type="button" className={activeExample === 'fashion' ? 'active' : ''} aria-pressed={activeExample === 'fashion'} onClick={() => setActiveExample('fashion')}>Fashion</button>
          </div>
          <span className="landing-demo-disclaimer">Illustrative sample only. Not a real product assessment.</span>
        </div>
        <article className={`landing-report-card report-${sample.color}`}>
          <div className="report-card-head"><span>{sample.category}</span><span className="report-card-id">DEMO · 00{activeExample === 'skincare' ? '1' : '2'}</span></div>
          <div className="report-product-row">
            <div className={`report-product-mark product-mark-${sample.color}`}>{sample.productMark}</div>
            <div><strong>{sample.product}</strong><small>{sample.subtitle}</small></div>
            <button type="button" className="report-more" aria-label="Sample report options">···</button>
          </div>
          <div className="report-verdict">
            <div className={`report-score score-${sample.color}`}><span>{sample.score}</span><small>/100</small></div>
            <div className="report-verdict-copy"><span className={`report-status status-${sample.color}`}><i />{sample.verdict}</span><strong>{sample.confidence} confidence</strong><p>{sample.explanation}</p></div>
          </div>
          <div className="report-evidence-heading"><strong>Evidence at a glance</strong><span>3 checks</span></div>
          <ul className="report-evidence-list">
            {sample.checks.map(([label, result, status]) => (
              <li key={label}><span className={`evidence-status evidence-${status}`}>{status === 'pending' ? '—' : '!'}</span><span>{label}</span><strong>{result}</strong></li>
            ))}
          </ul>
          <div className="report-not-checked"><span>i</span><span><strong>Not checked</strong><small>Contents can’t be verified from photos alone.</small></span></div>
          <div className="report-next-step"><span className="next-step-icon">↗</span><span><small>YOUR NEXT STEP</small><strong>{sample.next}</strong></span><ArrowIcon /></div>
          <p className="report-footnote">A trust score is a guide—not proof of authenticity. Never “100% genuine.”</p>
        </article>
      </section>

      <section className="landing-assistant">
        <div className="assistant-icon"><span>✳</span><i>↗</i></div>
        <div className="assistant-copy"><span>FOR PEOPLE AND AI ASSISTANTS</span><h2>One checker. More ways to use it.</h2><p>Check an item yourself, or let your AI assistant ask CheckAm to verify a product before you buy.</p></div>
        <div className="assistant-code"><span><i /> CheckAm CONNECTOR</span><code>verifyProduct(item)</code><small>Same checks. Same evidence.</small></div>
      </section>

      <footer className="landing-footer">
        <a className="landing-brand" href="#top"><CheckAmMark /><span>CheckAm<span className="landing-brand-period">.</span></span></a>
        <span className="landing-footer-note">Check thoughtfully. Buy confidently.</span>
        <a href="#top" className="landing-back-top">Back to top ↑</a>
      </footer>
    </main>
    )}
    {page === 'checking' && intake && <CheckingPage
      intake={intake}
      scanId={scanId}
      onBack={navigateBackFromChecking}
      onComplete={navigateToResult}
    />}
    {page === 'result' && result && <ResultPage result={result} onBack={navigateHome} />}
    <DemoPresetToolbar onSelect={navigateToChecking} />
    </>
  )
}

export default App
