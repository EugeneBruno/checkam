import { useEffect, useState } from 'react'
import checkAmLogo from '../public/Check_Am_Logo-removebg-preview.png'
import { NAPAMS_URL, confirmNapams, report, researchScan } from '../api.js'
import { toCheck } from './CheckingPage.jsx'
import BrandLoader from '../components/brand/BrandLoader.jsx'

const VERDICTS = {
  likely_genuine: {
    label: 'Likely genuine', tone: 'good',
    meaning: 'The official record matches this product and nothing we checked looked wrong.',
  },
  suspicious: {
    label: 'Suspicious', tone: 'warn',
    meaning: 'At least one thing doesn’t match what a genuine product should show.',
  },
  likely_fake: {
    label: 'Likely fake', tone: 'bad',
    meaning: 'We found strong evidence that this is not the genuine product.',
  },
  insufficient_evidence: {
    label: 'Not confirmed', tone: 'neutral',
    meaning: 'We couldn’t confirm this product either way. That is not the same as fake: we just didn’t have enough to go on.',
  },
}

const RECOMMENDATIONS = {
  buy: 'OK to buy',
  safe_to_use: 'OK to use',
  caution: 'Check further before you buy or use it',
  do_not_buy: 'Don’t buy it',
  do_not_use: 'Don’t use it',
}

const CONFIDENCE = {
  high: 'High: several independent checks agree',
  medium: 'Medium: some checks could be done',
  low: 'Low: only a few checks could be done',
}

const TONE = {
  good: { bg: '#E7F4EA', border: '#3E8E5A', text: '#1F5A35' },
  warn: { bg: '#FFF4DE', border: '#D99A2B', text: '#7A4E06' },
  bad: { bg: '#FDE8E6', border: '#C8463B', text: '#7D1F17' },
  neutral: { bg: '#EEF1EC', border: '#8DA99A', text: '#203C32' },
}

// first sentence of a check's detail, for the short "why" list
function short(text) {
  const t = String(text || '').trim()
  const cut = t.search(/\.(\s|$)/)
  return cut > 0 && cut < 180 ? t.slice(0, cut + 1) : t.slice(0, 180)
}

function Reason({ kind, check }) {
  const style = {
    problem: { mark: '!', color: '#B4473B', bg: '#FDE8E6' },
    ok: { mark: '✓', color: '#2E7A4A', bg: '#E7F4EA' },
    gap: { mark: '?', color: '#6B7A70', bg: '#EEF1EC' },
  }[kind]
  return (
    <li style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', marginTop: '0.45rem' }}>
      <span aria-hidden="true" style={{ flex: '0 0 1.4rem', height: '1.4rem', borderRadius: '50%', background: style.bg, color: style.color, display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: '0.8rem' }}>{style.mark}</span>
      <span><strong>{check.name}:</strong> {short(check.detail)}</span>
    </li>
  )
}

function ScoreDial({ score, color }) {
  const value = Math.max(0, Math.min(100, Number(score) || 0))
  const r = 44
  const c = 2 * Math.PI * r
  return (
    <div className="score-dial" aria-label={`Trust score ${value} out of 100`}>
      <svg viewBox="0 0 100 100" width="112" height="112" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(0,0,0,0.08)" strokeWidth="8" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} transform="rotate(-90 50 50)" className="score-dial-arc" />
      </svg>
      <div className="score-dial-text" style={{ color }}>
        <strong>{value}</strong>
        <small>/ 100</small>
      </div>
      <p className="score-dial-label">Trust score</p>
    </div>
  )
}

function VerdictCard({ response, checks }) {
  const v = VERDICTS[response.verdict] || VERDICTS.insufficient_evidence
  const tone = TONE[v.tone]
  const problems = checks.filter((c) => c.status === 'failed')
  const oks = checks.filter((c) => c.status === 'passed')
  const gaps = checks.filter((c) => c.status === 'unknown')
  const reasons = [
    ...problems.slice(0, 3).map((c) => ['problem', c]),
    ...(problems.length ? [] : oks.slice(0, 2).map((c) => ['ok', c])),
    ...(response.verdict === 'insufficient_evidence' || !problems.length ? gaps.slice(0, 2).map((c) => ['gap', c]) : []),
  ]
  return (
    <section className="telemetry-card verdict-card" style={{ background: tone.bg, borderColor: tone.border, borderWidth: 2 }} aria-label="Verdict">
      <div className="verdict-top">
        <div>
          <p className="telemetry-kicker" style={{ color: tone.text }}>VERDICT</p>
          <h2 className="verdict-title" style={{ color: tone.text }}>{v.label}</h2>
          <p className="verdict-action" style={{ color: tone.text }}>{RECOMMENDATIONS[response.recommendation] || response.recommendation}</p>
          <p style={{ color: tone.text, marginTop: '0.5rem' }}>{v.meaning}</p>
        </div>
        <ScoreDial score={response.trust_score} color={tone.border} />
      </div>

      {reasons.length > 0 && <div style={{ marginTop: '1rem' }}>
        <p style={{ fontWeight: 600, color: tone.text }}>Why</p>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: '#203C32' }}>
          {reasons.map(([kind, check]) => <Reason key={check.id} kind={kind} check={check} />)}
        </ul>
      </div>}

      {response.next_step && <p className="verdict-next" style={{ marginTop: '1rem', padding: '0.75rem 0.9rem', background: 'rgba(255,255,255,0.7)', borderRadius: 10, color: '#123E30' }}>
        <strong>What to do now:</strong> {response.next_step}
      </p>}

      <div className="summary-meta" style={{ marginTop: '0.9rem' }}>
        <span>Confidence: {CONFIDENCE[response.confidence] || response.confidence || '–'}</span>
        <span>{problems.length} problem{problems.length === 1 ? '' : 's'} · {oks.length} confirmed · {gaps.length} not confirmed</span>
        {response.prior_reports > 0 && <span>{response.prior_reports} buyer report{response.prior_reports === 1 ? '' : 's'}</span>}
      </div>
    </section>
  )
}

function EvidenceGroups({ checks }) {
  const groups = [
    ['Problems found', 'failed', 'These don’t match a genuine product.'],
    ['Confirmed', 'passed', 'These match the official record or look right.'],
    ['Not confirmed', 'unknown', 'We couldn’t check these. They are not problems by themselves.'],
  ]
  return (
    <section className="telemetry-card verification-card" aria-labelledby="evidence-heading">
      <p className="telemetry-kicker">EVIDENCE</p>
      <h2 id="evidence-heading">What was checked</h2>
      {groups.map(([title, status, hint]) => {
        const items = checks.filter((c) => c.status === status)
        if (!items.length) return null
        return (
          <div key={status} style={{ marginTop: '1.1rem' }}>
            <p className={`evidence-group-title evidence-group-${status}`}><strong>{title} ({items.length})</strong> <small>{hint}</small></p>
            <ul className="verification-list">
              {items.map((check) => (
                <li key={check.id} className={`verification-item verification-${check.status}`}>
                  <span className="verification-icon">{status === 'passed' ? '✓' : status === 'failed' ? '!' : '?'}</span>
                  <div className="verification-copy">
                    <strong>{check.name}</strong>
                    <small>{check.detail}</small>
                    {check.source && (/^https?:\/\//.test(check.source)
                      ? <small><a href={check.source} target="_blank" rel="noreferrer">Source ↗</a></small>
                      : <small>Source: {check.source}</small>)}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
      <p className="verification-live-note">A registry match shows the number belongs to this product. It can’t prove what’s inside the pack.</p>
    </section>
  )
}

function ProductCard({ response }) {
  const p = response.product || {}
  const ids = p.identifiers || {}
  const name = [p.brand, p.name].filter(Boolean).join(' · ') || p.looks_like || 'Product not named from the photos'
  const tags = [
    p.category && p.category.replace(/_/g, ' '),
    p.variant,
    ids.nafdac_no && `NAFDAC ${ids.nafdac_no}`,
    ids.batch && `Batch ${ids.batch}`,
    ids.expiry && `Expiry ${ids.expiry}`,
    ids.barcode && `Barcode ${ids.barcode}`,
    ids.imei && `IMEI ${ids.imei}`,
    ...(ids.son_marks || []).map((mark) => `SON ${mark}`),
    p.label_present === false && 'No label on the pack',
  ].filter(Boolean)
  return (
    <section className="intake-summary-card manual-product-summary" aria-label="What we read">
      <div className="summary-label"><span className="summary-icon">▤</span><div><small>WHAT WE READ</small><strong>{name}</strong></div></div>
      <div className="summary-meta">{tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
      {response.contents?.summary && <p style={{ marginTop: '0.5rem' }}><small>{response.contents.summary}</small></p>}
    </section>
  )
}

function ResearchCard({ research, route }) {
  if (!research && !route) return null
  return (
    <section className="telemetry-card" aria-label="How we checked">
      <p className="telemetry-kicker">HOW WE CHECKED</p>
      {route && <p><strong>{route.covered_locally ? 'Found in our local data.' : 'Not fully in our local data.'}</strong> {route.reason}{route.path ? ` (${route.path})` : ''}</p>}
      {research && <>
        <p style={{ marginTop: '0.5rem' }}>
          <strong>{research.cached ? 'Used saved research.' : 'Researched online.'}</strong>{' '}
          {research.verified ? 'Backed by the sources below.' : 'No specific product confirmed by a source: treat as general tips.'}
        </p>
        {research.summary && <p style={{ marginTop: '0.5rem' }}>{research.summary}</p>}
        {research.steps?.length > 0 && <details style={{ marginTop: '0.5rem' }}>
          <summary>Research steps ({research.steps.length})</summary>
          <ol style={{ paddingLeft: '1.25rem', marginTop: '0.5rem' }}>{research.steps.map((st, i) => <li key={i}><small>{st}</small></li>)}</ol>
        </details>}
        {research.sources?.length > 0 && <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
          {research.sources.map((src) => <li key={src.url}><a href={src.url} target="_blank" rel="noreferrer">{src.title || src.url}</a></li>)}
        </ul>}
      </>}
    </section>
  )
}

function ActionsCard({ response, intake, onUpdate }) {
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [note, setNote] = useState('')
  const actions = response.actions || []
  const nafdacNo = response.product?.identifiers?.nafdac_no

  async function run(kind, fn) {
    setBusy(kind)
    setMessage('')
    try {
      await fn()
    } catch (error) {
      setMessage(`Couldn’t do that: ${error.message}`)
    } finally {
      setBusy('')
    }
  }

  return (
    <section className="telemetry-card run-controls-card" aria-label="What you can do">
      <p className="telemetry-kicker">WHAT YOU CAN DO</p>
      {(response.links || []).map((link) => (
        <p key={link.url}><a href={link.url} target="_blank" rel="noreferrer">{link.label} ↗</a></p>
      ))}
      <div className="run-control-buttons" style={{ flexWrap: 'wrap' }}>
        {actions.includes('research') && <button type="button" disabled={!!busy} onClick={() => run('research', async () => {
          const next = await researchScan(response.scan_id)
          onUpdate(next)
          setMessage('Researched online. The result above is updated.')
        })}>{busy === 'research' ? 'Researching… (up to 20s)' : 'Research this product'}</button>}

        {actions.includes('confirm_on_napams') && <>
          <a className="control-secondary" style={{ display: 'inline-block', padding: '0.5rem 0.9rem' }} href={NAPAMS_URL} target="_blank" rel="noreferrer">Open NAPAMS ↗</a>
          <label className="control-secondary" style={{ display: 'inline-block', padding: '0.5rem 0.9rem', cursor: 'pointer' }}>
            {busy === 'napams' ? 'Reading screenshot…' : 'Send NAPAMS screenshot'}
            <input type="file" accept="image/*" hidden disabled={!!busy} onChange={(event) => {
              const file = event.target.files?.[0]
              event.target.value = ''
              if (file) run('napams', async () => {
                const r = await confirmNapams(file, nafdacNo)
                setMessage(r.message || 'Saved.')
              })
            }} />
          </label>
        </>}
      </div>
      {actions.includes('confirm_on_napams') && <p className="control-hint">On NAPAMS, type {nafdacNo || 'the NAFDAC number'}, tick “I’m not a robot”, press Verify, then send us a screenshot. Your check confirms it for every buyer after you.</p>}

      <div style={{ marginTop: '1rem' }}>
        <label className="field-label" htmlFor="report-note">Report this product <span>Optional note</span></label>
        <textarea id="report-note" rows="2" maxLength="600" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Where you saw it, the seller, what looked wrong…" />
        <div className="run-control-buttons">
          <button type="button" disabled={!!busy} onClick={() => run('report', async () => {
            await report({ scanId: response.scan_id, location: intake?.situation?.location, seller: intake?.product?.seller, note })
            setMessage('Reported. Other buyers who scan this product or batch will see it.')
            setNote('')
          })}>{busy === 'report' ? 'Sending…' : 'Report as suspicious'}</button>
        </div>
      </div>
      {message && <p className="control-hint" role="status" style={{ marginTop: '0.75rem' }}><strong>{message}</strong></p>}
      {busy === 'research' && <BrandLoader variant="overlay" label="Researching online…" sublabel="NAFDAC’s online Greenbook first, then official pages and alerts. Up to 20 seconds." />}
      {busy === 'napams' && <BrandLoader variant="overlay" label="Reading your NAPAMS screenshot…" />}
    </section>
  )
}

// Turn what Check Am read into the scan form's fields, so "check again" starts filled in
function toPrefill(response, intake) {
  const p = response?.product || {}
  const ids = p.identifiers || {}
  const typed = intake?.product || {}
  const pick = (...values) => values.find((v) => v !== undefined && v !== null && String(v).trim() !== '') || ''
  const out = {
    brand: pick(typed.brand, p.brand),
    productName: pick(typed.productName, p.name),
    category: pick(typed.category, p.category && p.category !== 'other' ? p.category.replace(/_/g, ' ') : ''),
    variant: pick(typed.variant, p.variant),
    nafdacNumber: pick(typed.nafdacNumber, ids.nafdac_no),
    batchNumber: pick(typed.batchNumber, ids.batch),
    expiryDate: pick(typed.expiryDate, ids.expiry),
    barcode: pick(typed.barcode, ids.barcode),
    imei: pick(typed.imei, ids.imei),
    imeiDevice: pick(typed.imeiDevice, ids.imei_device),
    seller: pick(typed.seller),
  }
  return Object.fromEntries(Object.entries(out).filter(([, v]) => v))
}

function ScanAgainBar({ response, intake, onScanAgain }) {
  if (!onScanAgain) return null
  return (
    <section className="telemetry-card run-controls-card" aria-label="Scan again">
      <div className="run-control-buttons" style={{ flexWrap: 'wrap' }}>
        {response && <button type="button" onClick={() => onScanAgain(toPrefill(response, intake))}>Add a photo and check this product again</button>}
        <button type="button" className="control-secondary" onClick={() => onScanAgain(null)}>Scan another product</button>
      </div>
    </section>
  )
}

// What a good set of photos should show, by product type, and whether we managed to read it
function readChecklist(response) {
  const p = response?.product || {}
  const ids = p.identifiers || {}
  const cat = p.category || 'other'
  const nafdac = ['drug', 'cosmetic', 'food', 'drink', 'spirits', 'water', 'herbal', 'medical_device'].includes(cat)
  const son = ['electrical', 'electronics', 'auto_part', 'building_material'].includes(cat)
  const rows = [['Brand and product name', p.brand || p.name]]
  if (nafdac) {
    rows.push(['NAFDAC number', ids.nafdac_no])
    rows.push(['Batch number', ids.batch])
    rows.push(['Expiry date', ids.expiry])
    rows.push(['Barcode', ids.barcode])
  } else if (cat === 'phone') {
    rows.push(['IMEI on the box', ids.imei])
    rows.push(['IMEI on the phone (*#06#)', ids.imei_device])
  } else if (son) {
    rows.push(['SON mark (MANCAP, NIS or PAM)', (ids.son_marks || []).join(', ')])
    rows.push(['Model / serial label', ids.serial || p.variant])
  } else {
    rows.push(['Barcode', ids.barcode])
  }
  return rows
}

function PhotosCard({ photos, response }) {
  const rows = readChecklist(response)
  const missing = rows.filter(([, v]) => !v)
  return (
    <section className="telemetry-card photos-card" aria-label="Your photos">
      <p className="telemetry-kicker">YOUR PHOTOS</p>
      <h2 className="photos-title">What we were working from</h2>
      {photos?.length > 0
        ? <div className="photo-strip">{photos.map((src, i) => <img key={i} src={src} alt={`Photo ${i + 1} you sent`} />)}</div>
        : <p className="verification-caption">No photos were sent for this check (typed details only).</p>}
      <ul className="read-list">
        {rows.map(([label, value]) => (
          <li key={label} className={value ? 'read-ok' : 'read-missing'}>
            <span aria-hidden="true">{value ? '✓' : '✗'}</span>
            <strong>{label}:</strong> {value ? String(value) : 'not readable in your photos'}
          </li>
        ))}
      </ul>
      {missing.length > 0 && <p className="photo-tip">
        <strong>For a better result,</strong> take a close, sharp, well-lit photo of the {missing.map(([l]) => (l.startsWith('NAFDAC') || l.startsWith('IMEI') || l.startsWith('SON') ? l : l.toLowerCase())).join(', ')}.
        Hold the phone steady, fill the frame with the label, and avoid glare.
      </p>}
    </section>
  )
}

function ResultPage({ result, onBack, onScanAgain }) {
  // open at the verdict, not wherever the checking page was scrolled to
  useEffect(() => { window.scrollTo(0, 0) }, [])
  const { intake, scanId, completedAt } = result
  const [response, setResponse] = useState(result.response || null)
  const purchaseStage = intake?.situation?.intent || 'BEFORE_BUYING'
  const checks = response ? (response.evidence || []).map(toCheck) : (result.checks || [])

  return (
    <main className="app-shell result-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CheckAm home" onClick={(event) => { event.preventDefault(); onBack() }}>
          <img
            src={checkAmLogo}
            alt="CheckAm"
            className="absolute left-0 -top-7 h-auto w-40 max-w-none"
          />
        </a>
        <div className="topbar-status"><span className="status-dot" /> Result</div>
        <button className="back-to-intake" type="button" onClick={onBack}>← Back to home</button>
      </header>
      <div className="page result-page">
        <div className="checking-breadcrumb"><span>NEW CHECK</span><i>/</i><span>CHECKING</span><i>/</i><strong>RESULT</strong></div>
        <div className="result-header">
          <p className="telemetry-kicker">CHECK AM RESULT · {response?.scan_id || scanId}</p>
          <h1>What the check <span>found.</span></h1>
          {intake?.situation?.summary && <p className="intro">{intake.situation.summary}</p>}
          {completedAt && <time dateTime={completedAt}>Completed {new Date(completedAt).toLocaleString()}</time>}
        </div>
        <div className="result-disclaimer" role="note">
          <strong>Evidence-based check, not a guarantee</strong>
          <span>Check Am compares the pack with NAFDAC, SON and NCC data, alerts and other buyers’ scans. It can’t test what’s inside the pack.</span>
        </div>

        {!response && <div className="result-disclaimer" role="alert">
          <strong>No result from Check Am</strong>
          <span>This page was opened without a live check. Go back and check the product again.</span>
        </div>}
        {!response && <ScanAgainBar response={null} intake={intake} onScanAgain={onScanAgain} />}

        {response && <>
          <VerdictCard response={response} checks={checks} />
          <ScanAgainBar response={response} intake={intake} onScanAgain={onScanAgain} />
          <PhotosCard photos={result.photos} response={response} />
          <ProductCard response={response} />
          <EvidenceGroups checks={checks} />
          <ActionsCard response={response} intake={intake} onUpdate={(next) => {
            setResponse(next)
            try {
              const key = `checkam:scan:${scanId}`
              const saved = JSON.parse(window.sessionStorage.getItem(key) || '{}')
              window.sessionStorage.setItem(key, JSON.stringify({ ...saved, response: next }))
            } catch { /* storage unavailable */ }
          }} />
          <ResearchCard research={response.research} route={response.route} />
          {response.not_checked?.length > 0 && <p className="verification-caption">Not checked: {response.not_checked.map((c) => c.replace(/_/g, ' ')).join(', ')}.</p>}
        </>}

        <section className={`telemetry-card stage-guidance stage-guidance-${purchaseStage.toLowerCase()}`}>
          <p className="telemetry-kicker">{purchaseStage === 'ALREADY_BOUGHT' ? 'POST-PURCHASE SAFETY' : 'PRE-PURCHASE GUIDANCE'}</p>
          <strong>{purchaseStage === 'ALREADY_BOUGHT' ? 'Already bought' : 'Before buying'}</strong>
          <p>{purchaseStage === 'ALREADY_BOUGHT'
            ? 'If the result is suspicious or uncertain, stop using it, keep the pack and receipt, and report it.'
            : 'If the result is suspicious or uncertain, don’t buy it until it’s verified.'}</p>
          <small>Not medical advice. For medicines, ask a pharmacist if you’re unsure.</small>
        </section>
        <ScanAgainBar response={response} intake={intake} onScanAgain={onScanAgain} />
        <footer className="page-footer"><span>Check Am · {response?.scan_id || scanId}</span><span>Completed {completedAt ? new Date(completedAt).toLocaleTimeString() : 'just now'}</span></footer>
      </div>
    </main>
  )
}

export default ResultPage
