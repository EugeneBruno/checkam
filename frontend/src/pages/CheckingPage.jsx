import { useCallback, useEffect, useRef, useState } from 'react'
import AgentThoughtLog from '../components/checking/AgentThoughtLog.jsx'
import StepProgressTracker from '../components/checking/StepProgressTracker.jsx'
import checkAmLogo from '../public/Check_Am_Logo-removebg-preview.png'
import { API_URL, makeThumbnails, takePendingFiles, verify } from '../api.js'
import BrandLoader from '../components/brand/BrandLoader.jsx'

// What the Check Am backend does for every scan, in order (see backend/pipeline.py)
const PIPELINE = [
  { id: 'send', label: 'Send photos and details', description: 'Upload to the Check Am server.' },
  { id: 'read', label: 'Read the pack', description: 'AI vision reads brand, NAFDAC number, batch, expiry, barcode, IMEI, SON marks.' },
  { id: 'route', label: 'Look in our local data', description: 'NAFDAC Greenbook copy, NAPAMS confirmations, SON list, NCC results, saved research.' },
  { id: 'checks', label: 'Run the checks', description: 'Registry fit, alerts, batch clones, barcode, dates, buyer reports, IMEI, SON.' },
  { id: 'research', label: 'Research online if needed', description: 'Only when the product is not in our data: NAFDAC online Greenbook, then the web.' },
  { id: 'verdict', label: 'Score the evidence', description: 'Fixed rules turn the evidence into a verdict and a next step.' },
]

// While we wait for the single /verify response, move through the steps the server is working on
const WAIT_SCHEDULE = [[0, 0], [1.2, 1], [4, 2], [5, 3], [8, 4]]

export const CHECK_NAMES = {
  registry_fit: 'NAFDAC registry match',
  nafdac_alerts: 'NAFDAC counterfeit alerts',
  clone_detection: 'Batch & serial clone check',
  prior_reports: 'Other buyers’ reports',
  barcode_check_digit: 'Barcode check digit',
  barcode_owner: 'Barcode belongs to this brand',
  date_sanity: 'Expiry & manufacture dates',
  son_certification: 'SON certification',
  imei_check: 'IMEI (box vs phone)',
  ncc_device_check: 'NCC device check',
  packaging_quality: 'Packaging & print quality',
  reference_match: 'Online research',
}

export function checkName(id) {
  return CHECK_NAMES[id] || String(id || 'check').replace(/_/g, ' ')
}

export function toCheck(evidence, index) {
  const status = evidence.result === 'pass' ? 'passed' : evidence.result === 'fail' ? 'failed' : 'unknown'
  return {
    id: `${evidence.check}-${index}`,
    name: checkName(evidence.check),
    detail: evidence.detail || '',
    source: evidence.source || null,
    status,
  }
}

function elapsedLabel(seconds) {
  const minutes = Math.floor(seconds / 60)
  const wholeSeconds = Math.floor(seconds % 60)
  const tenths = Math.floor((seconds % 1) * 10)
  return `${String(minutes).padStart(2, '0')}:${String(wholeSeconds).padStart(2, '0')}.${tenths}`
}

function statusIcon(status) {
  return status === 'passed' ? '✓' : status === 'failed' || status === 'warning' ? '!' : status === 'unknown' ? '?' : '·'
}

function statusLabel(status) {
  return status === 'passed' ? 'OK' : status === 'failed' || status === 'warning' ? 'PROBLEM' : status === 'unknown' ? 'NOT CONFIRMED' : 'RUNNING'
}

export function statusWord(status) { return statusLabel(status) }

export function VerificationPanel({ checks, live }) {
  const passed = checks.filter((check) => check.status === 'passed').length
  const flagged = checks.filter((check) => check.status === 'failed' || check.status === 'warning').length

  return (
    <section className="telemetry-card verification-card" aria-labelledby="verification-heading">
      <div className="telemetry-heading">
        <div>
          <p className="telemetry-kicker">EVIDENCE</p>
          <h2 id="verification-heading">What was checked</h2>
        </div>
        <span className={`verification-summary ${flagged ? 'verification-alert' : ''}`}>
          {passed} passed{flagged ? ` · ${flagged} flagged` : ''}
        </span>
      </div>
      <p className="verification-caption">Each line is one check with its source. “Not confirmed” means we couldn’t check it either way: it is not a problem by itself.</p>
      {checks.length === 0
        ? <div className="verification-empty">Checks appear here when Check Am answers.</div>
        : <ul className="verification-list" aria-live="polite">
          {checks.map((check) => (
            <li key={check.id} className={`verification-item verification-${check.status}`}>
              <span className="verification-icon">{statusIcon(check.status)}</span>
              <div className="verification-copy">
                <strong>{check.name}</strong>
                <small>{check.detail}</small>
                {check.source && (/^https?:\/\//.test(check.source)
                  ? <small><a href={check.source} target="_blank" rel="noreferrer">Source ↗</a></small>
                  : <small>Source: {check.source}</small>)}
              </div>
              <span className="verification-status">{statusLabel(check.status)}</span>
            </li>
          ))}
        </ul>}
      {live && <p className="verification-live-note">Evidence from Check Am. A registry match shows the number belongs to this product; it can’t prove what’s inside the pack.</p>}
    </section>
  )
}

function CheckingPage({ intake, scanId, onBack, onComplete }) {
  const [runStatus, setRunStatus] = useState('running')
  const [activeIndex, setActiveIndex] = useState(0)
  const [events, setEvents] = useState([])
  const [checks, setChecks] = useState([])
  const [elapsed, setElapsed] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const startRef = useRef(0)
  const filesRef = useRef(null)
  const completedRef = useRef(false)
  const requestRef = useRef(null)

  if (filesRef.current === null) filesRef.current = takePendingFiles(scanId)
  const files = filesRef.current

  const addEvent = useCallback((title, detail, status = '') => {
    const seconds = (Date.now() - startRef.current) / 1000
    setEvents((current) => [...current, {
      id: `ev-${current.length}-${Date.now()}`,
      kind: status === 'done' ? 'verification' : 'trace',
      title,
      detail,
      time: elapsedLabel(seconds),
      status,
    }].slice(-100))
  }, [])

  useEffect(() => {
    let cancelled = false
    const timers = []
    completedRef.current = false
    startRef.current = Date.now()
    setRunStatus('running')
    setActiveIndex(0)
    setEvents([])
    setChecks([])
    setElapsed(0)

    const typed = Object.values(intake.product || {}).filter((value) => String(value || '').trim()).length
    if (!files.length && !typed) {
      addEvent('Nothing to check', 'Go back and add a photo of the product or type at least one detail. (Photos are not kept if the page reloads.)', 'failed')
      setRunStatus('failed')
      return undefined
    }

    addEvent('Sending to Check Am', `${files.length} photo${files.length === 1 ? '' : 's'} and ${typed} typed detail${typed === 1 ? '' : 's'} → ${API_URL}`)
    WAIT_SCHEDULE.slice(1).forEach(([seconds, index]) => {
      timers.push(window.setTimeout(() => {
        if (cancelled || completedRef.current) return
        setActiveIndex(index)
        addEvent(PIPELINE[index].label, PIPELINE[index].description, 'waiting')
      }, seconds * 1000))
    })

    // one request per attempt, even when React (StrictMode) runs this effect twice
    if (requestRef.current?.attempt !== attempt) {
      requestRef.current = {
        attempt,
        promise: verify({
          files,
          product: intake.product,
          situation: intake.situation?.intent,
          location: intake.situation?.location,
        }),
      }
    }
    const thumbsPromise = makeThumbnails(files)
    Promise.all([requestRef.current.promise, thumbsPromise]).then(([response, photos]) => {
      if (cancelled) return
      completedRef.current = true
      timers.forEach(window.clearTimeout)
      const p = response.product || {}
      addEvent('Pack read', [p.brand, p.name, p.variant].filter(Boolean).join(' · ') || p.looks_like || 'Product could not be named from the photos', 'done')
      if (response.route) {
        addEvent(response.route.covered_locally ? 'Found in our local data' : 'Not fully covered by our local data',
          `${response.route.reason || ''} → ${response.route.path || ''}`, 'done')
      }
      for (const st of response.research?.steps || []) addEvent('Research', st, 'done')
      const finalChecks = (response.evidence || []).map(toCheck)
      setChecks(finalChecks)
      addEvent('Verdict', `${String(response.verdict || '').replace(/_/g, ' ')} · trust score ${response.trust_score ?? '–'}`, 'done')
      setActiveIndex(PIPELINE.length - 1)
      setRunStatus('completed')
      window.setTimeout(() => onComplete({ scanId, intake, checks: finalChecks, response, photos }), 1200)
    }).catch((error) => {
      if (cancelled) return
      completedRef.current = true
      timers.forEach(window.clearTimeout)
      const offline = /Failed to fetch|NetworkError|Load failed/i.test(error.message)
      addEvent('Check failed', offline
        ? `Can't reach the Check Am server at ${API_URL}. Is uvicorn running?`
        : error.message, 'failed')
      setRunStatus('failed')
    })

    return () => {
      cancelled = true
      timers.forEach(window.clearTimeout)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  useEffect(() => {
    if (runStatus !== 'running') return undefined
    const timer = window.setInterval(() => setElapsed((current) => current + 1), 1000)
    return () => window.clearInterval(timer)
  }, [runStatus])

  const statusText = runStatus === 'completed' ? 'Check complete' : runStatus === 'failed' ? 'Check failed' : 'Checking…'
  const purchaseStage = intake.situation.intent || 'BEFORE_BUYING'
  const purchaseStageLabel = purchaseStage === 'ALREADY_BOUGHT' ? 'Already bought' : 'Before buying'

  return (
    <main className="app-shell checking-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CheckAm home" onClick={(event) => { event.preventDefault(); onBack() }}>
          <img
            src={checkAmLogo}
            alt="CheckAm"
        className="absolute left-0 -top-7 h-auto w-40 max-w-none"
          />
        </a>
        <div className="topbar-status"><span className="status-dot" /> Checking · {elapsed}s</div>
        <button className="back-to-intake" type="button" onClick={onBack}>← Back</button>
      </header>

      <div className="page checking-page">
        <div className="checking-breadcrumb"><span>NEW CHECK</span><i>/</i><strong>CHECKING</strong></div>
        <div className="checking-title-row">
          <div>
            <div className="eyebrow"><span>02</span> CHECKING</div>
            <h1>Checking <span>your product.</span></h1>
            <p className="intro">Check Am reads the pack, looks it up in NAFDAC, SON and NCC data, and researches online only when it has to.</p>
          </div>
          <div className={`run-state run-${runStatus}`}><span />{statusText}</div>
        </div>

        {runStatus === 'running' && <BrandLoader label="Checking your product…" sublabel={`${PIPELINE[activeIndex]?.label || 'Working'} · ${elapsed}s`} />}

        <section className="intake-summary-card" aria-label="Current intake summary">
          <div className="summary-label"><span className="summary-icon">▤</span><div><small>PRODUCT</small><strong>{intake.situation.summary || [intake.product?.brand, intake.product?.productName].filter(Boolean).join(' ') || 'Product check'}</strong></div></div>
          <div className="summary-meta"><span className={`urgency-tag intent-tag intent-${purchaseStage.toLowerCase()}`}>{purchaseStageLabel}</span><span>{files.length} photo{files.length === 1 ? '' : 's'}</span>{intake.situation.location && <span>{intake.situation.location}</span>}</div>
        </section>
        {intake.product && Object.values(intake.product).some((value) => typeof value === 'string' && value.trim()) && <section className="intake-summary-card manual-product-summary" aria-label="Manually entered product details">
          <div className="summary-label"><span className="summary-icon">≡</span><div><small>DETAILS YOU TYPED</small><strong>{intake.product.productName || intake.product.brand || intake.product.category || 'Product details provided'}</strong></div></div>
          <div className="summary-meta">{[intake.product.brand, intake.product.variant, intake.product.barcode && `Barcode ${intake.product.barcode}`, intake.product.nafdacNumber && `NAFDAC ${intake.product.nafdacNumber}`, intake.product.sonNumber && `SON ${intake.product.sonNumber}`, intake.product.batchNumber && `Batch ${intake.product.batchNumber}`, intake.product.imei && `IMEI ${intake.product.imei}`].filter(Boolean).map((value) => <span key={value}>{value}</span>)}</div>
        </section>}
        {intake.preset && <section className="demo-preset-result" aria-label="Demo preset details">
          <div><span>JUDGE PRESET · {intake.preset.label.toUpperCase()}</span><strong>{intake.preset.outcome}</strong></div>
          <p>{intake.preset.simulation}</p>
        </section>}

        <div className="telemetry-layout">
          <div className="telemetry-main">
            <AgentThoughtLog events={events} live />
            <VerificationPanel checks={checks} live />
          </div>
          <aside className="telemetry-side">
            <StepProgressTracker steps={PIPELINE} activeIndex={activeIndex} status={runStatus} />
            <section className="telemetry-card run-controls-card">
              <p className="telemetry-kicker">RUN CONTROLS</p>
              <div className="run-control-buttons">
                {runStatus === 'failed' && <button type="button" onClick={() => setAttempt((n) => n + 1)}>↻ Try again</button>}
                <button type="button" className="control-secondary" onClick={onBack}>← Back</button>
              </div>
              <p className="control-hint">A first check of a new product can take 15–20 seconds while Check Am researches it. Repeat checks are instant.</p>
            </section>
          </aside>
        </div>

        <footer className="page-footer"><span>Check Am</span><span>Evidence, not a guarantee. When in doubt, don’t buy or use it.</span></footer>
      </div>
    </main>
  )
}

export default CheckingPage
