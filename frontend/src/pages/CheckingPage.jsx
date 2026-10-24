import { useCallback, useEffect, useRef, useState } from 'react'
import AgentThoughtLog from '../components/checking/AgentThoughtLog.jsx'
import SimulatedTelemetry from '../components/checking/SimulatedTelemetry.jsx'
import StepProgressTracker from '../components/checking/StepProgressTracker.jsx'
import checkAmLogo from '../public/Check_Am_Logo-removebg-preview.png'

const demoSteps = [
  {
    id: 'category',
    label: 'Identify product category & packaging',
    description: 'Classify the supplied product details.',
    title: 'Identifying product category & packaging...',
    detail: 'Demo classification step; no autonomous vision model is connected.',
  },
  {
    id: 'markings',
    label: 'Extract regulatory markings',
    description: 'Inspect the NAFDAC / SON fields provided.',
    title: 'Extracting NAFDAC / SON regulatory markings via OCR...',
    detail: 'OCR activity is simulated from supplied intake fields; no image processing runs.',
  },
  {
    id: 'registry',
    label: 'Query registry gazette & approvals',
    description: 'Prepare a registry comparison.',
    title: 'Querying verified registry gazette & active approvals...',
    detail: 'Registry lookup is simulated; no public records or live approvals are queried.',
  },
  {
    id: 'geography',
    label: 'Cross-reference geographical scan ledger',
    description: 'Check for a sample duplicate-location signal.',
    title: 'Cross-referencing geographical scan ledger for clone anomalies...',
    detail: 'Geographical anomaly check uses only scripted demo signals; no location ledger is connected.',
  },
  {
    id: 'visual-analysis',
    label: 'Synthesize visual logo & typography signals',
    description: 'Prepare a final review summary.',
    title: 'Synthesizing visual logo & typography discrepancy analysis...',
    detail: 'Visual discrepancy analysis is simulated; submitted images are not analyzed.',
  },
]

const demoChecks = [
  { id: 'summary', name: 'Situation summary present' },
  { id: 'context', name: 'Context fields represented' },
  { id: 'media', name: 'Attachment metadata indexed' },
  { id: 'safety', name: 'Safety framing included' },
  { id: 'transmission', name: 'No external transmission' },
]

function evaluateChecks(intake) {
  const { situation, attachments } = intake
  const product = intake.product || {}
  const summary = situation.summary.trim()
  const metadataComplete = attachments.every((attachment) =>
    Boolean(attachment.name && attachment.type && Number.isFinite(attachment.sizeBytes)),
  )
  const contextComplete = Boolean(situation.location && situation.safeToApproach)
  const suppliedProductDetails = Object.values(product).filter((value) => typeof value === 'string' && value.trim()).length
  const purchaseStage = situation.intent || 'BEFORE_BUYING'

  const intakeChecks = [
    {
      ...demoChecks[0],
      status: summary.length >= 20 ? 'passed' : 'warning',
      detail: summary.length >= 20
        ? 'A descriptive situation summary was supplied.'
        : 'The summary is brief; consider adding observable details.',
    },
    {
      ...demoChecks[1],
      status: contextComplete ? 'passed' : 'warning',
      detail: contextComplete
        ? 'Location and approach-safety context are present.'
        : `Missing ${[
          !situation.location && 'location',
          !situation.safeToApproach && 'approach-safety context',
        ].filter(Boolean).join(' and ')}; these fields are optional but may help review.`,
    },
    {
      ...demoChecks[2],
      status: metadataComplete ? 'passed' : 'failed',
      detail: attachments.length === 0
        ? 'No attachments were submitted; there is no media metadata to index.'
        : metadataComplete
          ? `${attachments.length} attachment${attachments.length === 1 ? '' : 's'} have names, types, and sizes.`
          : 'One or more attachments are missing required metadata.',
    },
    {
      id: 'manual-product-details',
      name: 'Manual product details captured',
      status: suppliedProductDetails > 0 ? 'passed' : 'warning',
      detail: suppliedProductDetails > 0
        ? `${suppliedProductDetails} product detail field${suppliedProductDetails === 1 ? '' : 's'} supplied by the user; not independently verified.`
        : 'No manual product details supplied. Details may be entered when labels are unreadable.',
    },
    {
      ...demoChecks[3],
      status: situation.safeToApproach ? 'passed' : 'warning',
      detail: situation.safeToApproach
        ? `Approach-safety response recorded: ${situation.safeToApproach}.`
        : 'No approach-safety response was provided.',
    },
    {
      ...demoChecks[4],
      status: 'passed',
      detail: 'This local demo does not upload media or contact external research services.',
    },
    {
      id: 'situational-guidance',
      name: 'Guidance matched to purchase stage',
      status: 'passed',
      detail: purchaseStage === 'ALREADY_BOUGHT'
        ? 'Post-purchase mode: if authenticity or safety is uncertain, quarantine the item and do not consume it until verified.'
        : 'Pre-purchase mode: if evidence is suspicious or insufficient, do not buy until the product is independently verified.',
    },
  ]

  return [...intakeChecks, ...(intake.preset?.checks || [])]
}

function initialTrace() {
  return [{
    id: 'demo-start',
    kind: 'trace',
    title: 'Verification sequence initialized',
    detail: 'Simulated terminal trace; no public records, images, or geographic ledgers are queried.',
    time: '00:00',
  }]
}

function elapsedLabel(seconds) {
  const minutes = Math.floor(seconds / 60)
  const wholeSeconds = Math.floor(seconds % 60)
  const tenths = Math.floor((seconds % 1) * 10)
  return `${String(minutes).padStart(2, '0')}:${String(wholeSeconds).padStart(2, '0')}.${tenths}`
}

function VerificationPanel({ checks, live }) {
  const passed = checks.filter((check) => check.status === 'passed').length
  const flagged = checks.filter((check) => check.status === 'failed' || check.status === 'warning').length

  return (
    <section className="telemetry-card verification-card" aria-labelledby="verification-heading">
      <div className="telemetry-heading">
        <div>
          <p className="telemetry-kicker">QUALITY GATES</p>
          <h2 id="verification-heading">Heuristic verification</h2>
        </div>
        <span className={`verification-summary ${flagged ? 'verification-alert' : ''}`}>
          {passed} passed{flagged ? ` · ${flagged} flagged` : ''}
        </span>
      </div>
      <p className="verification-caption">Rule-based signals for review—not a truth or safety guarantee.</p>
      {checks.length === 0
        ? <div className="verification-empty">Checks will appear as the run progresses.</div>
        : <ul className="verification-list" aria-live="polite">
          {checks.map((check) => (
            <li key={check.id} className={`verification-item verification-${check.status}`}>
              <span className="verification-icon">{check.status === 'passed' ? '✓' : check.status === 'failed' || check.status === 'warning' ? '!' : '·'}</span>
              <div className="verification-copy">
                <strong>{check.name}</strong>
                <small>{check.detail}</small>
              </div>
              <span className="verification-status">{check.status === 'passed' ? 'PASS' : check.status === 'failed' || check.status === 'warning' ? 'FLAG' : 'RUNNING'}</span>
            </li>
          ))}
        </ul>}
      {live && <p className="verification-live-note">Results are provided by the connected agent; verify them independently.</p>}
    </section>
  )
}

function CheckingPage({ intake, scanId, onBack, onComplete }) {
  const [source, setSource] = useState('demo')
  const [runStatus, setRunStatus] = useState('running')
  const [activeIndex, setActiveIndex] = useState(-1)
  const [events, setEvents] = useState(initialTrace)
  const [checks, setChecks] = useState([])
  const [elapsed, setElapsed] = useState(0)
  const elapsedRef = useRef(0)
  const completedRef = useRef(false)

  const completeRun = useCallback((finalChecks) => {
    if (completedRef.current) return
    completedRef.current = true
    setChecks(finalChecks)
    setRunStatus('completed')
    onComplete({ scanId, intake, checks: finalChecks })
  }, [intake, onComplete, scanId])

  useEffect(() => {
    elapsedRef.current = elapsed
  }, [elapsed])

  useEffect(() => {
    if (source !== 'demo' || runStatus !== 'running') return undefined

    const timer = window.setTimeout(() => {
      const nextIndex = activeIndex + 1
      const step = demoSteps[nextIndex]
      if (!step) {
        setRunStatus('completed')
        return
      }

      const nextElapsed = (nextIndex + 1) * 0.45
      setActiveIndex(nextIndex)
      setElapsed(Math.floor(nextElapsed))
      setEvents((current) => [...current, {
        id: `demo-${step.id}`,
        kind: 'trace',
        title: step.title,
        detail: step.detail,
        time: elapsedLabel(nextElapsed),
      }])
      const allChecks = evaluateChecks(intake)
      if (nextIndex === demoSteps.length - 1) {
        completeRun(allChecks)
      } else {
        setChecks(allChecks.slice(0, Math.min(allChecks.length, nextIndex + 1)))
      }
    }, 450)

    return () => window.clearTimeout(timer)
  }, [activeIndex, completeRun, intake, runStatus, source])

  useEffect(() => {
    if (runStatus !== 'running') return undefined
    const timer = window.setInterval(() => setElapsed((current) => current + 1), 1000)
    return () => window.clearInterval(timer)
  }, [runStatus])

  useEffect(() => {
    function handleAgentEvent(event) {
      const detail = event.detail
      if (!detail || typeof detail !== 'object') return

      if (detail.type === 'trace' && typeof detail.title === 'string' && typeof detail.detail === 'string') {
        setSource('live')
        setEvents((current) => [...current, {
          id: typeof detail.id === 'string' ? detail.id : `live-${Date.now()}-${current.length}`,
          kind: 'trace',
          title: detail.title.slice(0, 160),
          detail: detail.detail.slice(0, 1200),
          time: typeof detail.time === 'string' ? detail.time.slice(0, 32) : elapsedLabel(elapsedRef.current),
          status: typeof detail.status === 'string' ? detail.status.slice(0, 32) : '',
        }].slice(-100))
        if (detail.status === 'failed') setRunStatus('failed')
        else if (detail.status === 'completed') completeRun(evaluateChecks(intake))
        else setRunStatus('running')
      } else if (detail.type === 'verification' && typeof detail.name === 'string') {
        setSource('live')
        const status = ['passed', 'failed', 'warning', 'running'].includes(detail.status) ? detail.status : 'running'
        setChecks((current) => {
          const next = {
            id: typeof detail.id === 'string' ? detail.id : detail.name.slice(0, 160),
            name: detail.name.slice(0, 160),
            detail: typeof detail.detail === 'string' ? detail.detail.slice(0, 1200) : '',
            status,
          }
          const existing = current.findIndex((check) => check.id === next.id)
          if (existing < 0) return [...current, next].slice(-50)
          return current.map((check, index) => index === existing ? next : check)
        })
      } else if (detail.type === 'status' && ['running', 'paused', 'completed', 'failed'].includes(detail.status)) {
        setSource('live')
        if (detail.status === 'completed') completeRun(evaluateChecks(intake))
        else setRunStatus(detail.status)
      }
    }

    window.addEventListener('checkam:agent-event', handleAgentEvent)
    return () => window.removeEventListener('checkam:agent-event', handleAgentEvent)
  }, [completeRun, intake])

  function restartDemo() {
    setSource('demo')
    setRunStatus('running')
    completedRef.current = false
    setActiveIndex(-1)
    setEvents(initialTrace())
    setChecks([])
    setElapsed(0)
  }

  const running = runStatus === 'running'
  const statusLabel = runStatus === 'completed' ? 'Run complete' : runStatus === 'failed' ? 'Run failed' : runStatus === 'paused' ? 'Paused' : 'Agent active'
  const urgency = intake.situation.urgency === 'urgent' ? 'Urgent' : intake.situation.urgency === 'soon' ? 'Needs attention' : 'Routine'
  const purchaseStage = intake.situation.intent || 'BEFORE_BUYING'
  const purchaseStageLabel = purchaseStage === 'ALREADY_BOUGHT' ? 'Already bought' : 'Before buying'
  const recommendation = purchaseStage === 'ALREADY_BOUGHT'
    ? 'If this item may be unsafe or counterfeit, quarantine it and do not consume it until verified.'
    : 'If evidence is suspicious or incomplete, do not buy until you can verify the product.'
  const displayedSteps = source === 'live'
    ? events.filter((event) => event.kind === 'trace').map((event) => ({
      id: event.id,
      label: event.title,
      description: event.detail,
    }))
    : demoSteps
  const displayedStepIndex = source === 'live'
    ? Math.max(0, displayedSteps.length - 1)
    : activeIndex

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
        <div className="topbar-status"><span className="status-dot" /> Research workspace</div>
        <button className="back-to-intake" type="button" onClick={onBack}>← Back to intake</button>
      </header>

      <div className="page checking-page">
        <div className="checking-breadcrumb"><span>FIELD INTAKE</span><i>/</i><strong>RESEARCH TRACE</strong></div>
        <div className="checking-title-row">
          <div>
            <div className="eyebrow"><span>02</span> EXECUTION MONITOR</div>
            <h1>Research <span>in motion.</span></h1>
            <p className="intro">Follow the run, inspect its activity, and review heuristic checks as they arrive.</p>
          </div>
          <div className={`run-state run-${runStatus}`}><span />{statusLabel}</div>
        </div>

        <div className="demo-notice" role="note">
          <span className="demo-notice-icon">i</span>
          <p><strong>{source === 'live' ? 'Live event feed connected' : 'Illustrative demo trace'}</strong>{source === 'live'
            ? ' — incoming events are shown as received. This interface does not verify agent claims.'
            : ' — no autonomous research agent is connected, and no external research is being performed.'}</p>
        </div>

        <section className="intake-summary-card" aria-label="Current intake summary">
          <div className="summary-label"><span className="summary-icon">▤</span><div><small>ACTIVE INTAKE</small><strong>{intake.situation.summary || 'Situation summary not provided'}</strong></div></div>
          <div className="summary-meta"><span className={`urgency-tag intent-tag intent-${purchaseStage.toLowerCase()}`}>{purchaseStageLabel}</span><span className={`urgency-tag urgency-${intake.situation.urgency}`}>{urgency}</span><span>{intake.attachments.length} attachment{intake.attachments.length === 1 ? '' : 's'}</span>{intake.situation.location && <span>{intake.situation.location}</span>}</div>
        </section>
        {intake.product && Object.values(intake.product).some((value) => typeof value === 'string' && value.trim()) && <section className="intake-summary-card manual-product-summary" aria-label="Manually entered product details">
          <div className="summary-label"><span className="summary-icon">≡</span><div><small>USER-ENTERED PRODUCT DETAILS</small><strong>{intake.product.productName || intake.product.brand || intake.product.category || 'Product details provided'}</strong></div></div>
          <div className="summary-meta">{[intake.product.brand, intake.product.variant, intake.product.barcode && `Barcode ${intake.product.barcode}`, intake.product.nafdacNumber && `NAFDAC ${intake.product.nafdacNumber}`, intake.product.sonNumber && `SON ${intake.product.sonNumber}`, intake.product.batchNumber && `Batch ${intake.product.batchNumber}`].filter(Boolean).map((value) => <span key={value}>{value}</span>)}</div>
        </section>}
        {intake.preset && <section className="demo-preset-result" aria-label="Demo preset details">
          <div><span>SIMULATED SCENARIO · {intake.preset.label.toUpperCase()}</span><strong>{intake.preset.outcome}</strong></div>
          <p>{intake.preset.simulation}</p>
        </section>}

        <div className="telemetry-layout">
          <div className="telemetry-main">
            <AgentThoughtLog events={events} live={source === 'live'} />
            <VerificationPanel checks={checks} live={source === 'live'} />
            <section className={`telemetry-card stage-guidance stage-guidance-${purchaseStage.toLowerCase()}`} aria-label="Situation-specific guidance">
              <p className="telemetry-kicker">{purchaseStage === 'ALREADY_BOUGHT' ? 'POST-PURCHASE SAFETY' : 'PRE-PURCHASE GUIDANCE'}</p>
              <strong>{purchaseStage === 'ALREADY_BOUGHT' ? 'Already bought' : 'Before buying'}</strong>
              <p>{recommendation}</p>
              <small>This is precautionary guidance, not a product-authenticity verdict or medical advice.</small>
            </section>
          </div>
          <aside className="telemetry-side">
            <SimulatedTelemetry elapsed={elapsed} running={running} live={source === 'live'} />
            <StepProgressTracker steps={displayedSteps} activeIndex={displayedStepIndex} status={runStatus} />
            <section className="telemetry-card run-controls-card">
              <p className="telemetry-kicker">RUN CONTROLS</p>
              <div className="run-control-buttons">
                {source === 'demo' && runStatus !== 'completed' && <button type="button" onClick={() => setRunStatus(running ? 'paused' : 'running')}>{running ? 'Ⅱ Pause demo' : '▶ Resume demo'}</button>}
                {source === 'demo' && <button type="button" className="control-secondary" onClick={restartDemo}>↻ Restart demo</button>}
              </div>
              <p className="control-hint">{source === 'live' ? 'Run state is supplied by the event feed.' : 'The demo advances through a sample trace locally.'}</p>
            </section>
            <section className="telemetry-card intake-facts">
              <p className="telemetry-kicker">INTAKE SNAPSHOT</p>
              <dl>
                <div><dt>Time sensitivity</dt><dd>{urgency}</dd></div>
                <div><dt>Approach safety</dt><dd>{intake.situation.safeToApproach || 'Not specified'}</dd></div>
                <div><dt>People involved</dt><dd>{intake.situation.peopleInvolved || 'Not specified'}</dd></div>
                <div><dt>Additional context</dt><dd>{intake.situation.additionalDetails ? 'Provided' : 'Not provided'}</dd></div>
              </dl>
            </section>
          </aside>
        </div>

        <details className="event-contract">
          <summary>Integrate an agent event feed</summary>
          <p>Dispatch a <code>checkam:agent-event</code> CustomEvent on <code>window</code>. Supported detail payloads:</p>
          <pre>{`{ type: 'trace', title: 'Searching source', detail: 'Query sent to source index' }
{ type: 'verification', id: 'source-check', name: 'Source coverage', detail: '3 sources checked', status: 'passed' }
{ type: 'status', status: 'running' }`}</pre>
          <p>Trace status may be <code>completed</code> or <code>failed</code>. Verification status accepts <code>passed</code>, <code>warning</code>, <code>failed</code>, or <code>running</code>. Invalid events are ignored.</p>
        </details>
        <footer className="page-footer"><span>CheckAm EXECUTION MONITOR</span><span>Heuristics are review signals, not a guarantee of accuracy.</span></footer>
      </div>
    </main>
  )
}

export default CheckingPage