function ResultPage({ result, onBack }) {
  const { intake, checks, scanId, completedAt } = result
  const flagged = checks.filter((check) => check.status === 'failed' || check.status === 'warning')
  const passed = checks.filter((check) => check.status === 'passed')
  const purchaseStage = intake.situation.intent || 'BEFORE_BUYING'
  const recommendation = purchaseStage === 'ALREADY_BOUGHT'
    ? 'If authenticity or safety is uncertain, quarantine the item and do not consume it until independently verified.'
    : 'If evidence is suspicious or incomplete, do not buy until the product is independently verified.'

  return (
    <main className="app-shell result-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CheckAm home" onClick={(event) => { event.preventDefault(); onBack() }}>
          <span className="brand-mark">c</span>
          <span>CheckAm<span className="brand-dot">.</span></span>
        </a>
        <div className="topbar-status"><span className="status-dot" /> Review summary</div>
        <button className="back-to-intake" type="button" onClick={onBack}>← Back to home</button>
      </header>
      <div className="page result-page">
        <div className="checking-breadcrumb"><span>FIELD INTAKE</span><i>/</i><span>RESEARCH TRACE</span><i>/</i><strong>RESULT</strong></div>
        <div className="result-header">
          <p className="telemetry-kicker">LOCAL REVIEW SUMMARY · {scanId}</p>
          <h1>What the check <span>found.</span></h1>
          <p className="intro">{intake.situation.summary || 'No situation summary was provided.'}</p>
          {completedAt && <time dateTime={completedAt}>Completed {new Date(completedAt).toLocaleString()}</time>}
        </div>
        <div className="result-disclaimer" role="note">
          <strong>Illustrative demo result</strong>
          <span>This local simulation does not access public records, analyze images, or verify product authenticity.</span>
        </div>
        {intake.preset && <section className="demo-preset-result" aria-label="Simulated scenario">
          <div><span>SIMULATED SCENARIO · {intake.preset.label.toUpperCase()}</span><strong>{intake.preset.outcome}</strong></div>
          <p>{intake.preset.simulation}</p>
        </section>}
        {intake.product && <section className="intake-summary-card manual-product-summary" aria-label="Product details">
          <div className="summary-label"><span className="summary-icon">▤</span><div><small>USER-ENTERED PRODUCT DETAILS</small><strong>{intake.product.productName || intake.product.brand || 'Product details provided'}</strong></div></div>
          <div className="summary-meta">{[intake.product.brand, intake.product.variant, intake.product.nafdacNumber && `NAFDAC ${intake.product.nafdacNumber}`, intake.product.sonNumber && `SON ${intake.product.sonNumber}`, intake.product.batchNumber && `Batch ${intake.product.batchNumber}`].filter(Boolean).map((value) => <span key={value}>{value}</span>)}</div>
        </section>}
        <section className="telemetry-card result-checks" aria-labelledby="result-checks-heading">
          <div className="telemetry-heading">
            <div><p className="telemetry-kicker">HEURISTIC REVIEW</p><h2 id="result-checks-heading">Signals to review</h2></div>
            <span className={`verification-summary ${flagged.length ? 'verification-alert' : ''}`}>{passed.length} passed{flagged.length ? ` · ${flagged.length} flagged` : ''}</span>
          </div>
          <p className="verification-caption">These are demo and intake-quality signals—not a truth or safety guarantee.</p>
          <ul className="verification-list">
            {checks.map((check) => (
              <li key={check.id} className={`verification-item verification-${check.status}`}>
                <span className="verification-icon">{check.status === 'passed' ? '✓' : check.status === 'failed' || check.status === 'warning' ? '!' : '·'}</span>
                <div className="verification-copy"><strong>{check.name}</strong><small>{check.detail}</small></div>
                <span className="verification-status">{check.status === 'passed' ? 'PASS' : check.status === 'failed' || check.status === 'warning' ? 'FLAG' : 'RUNNING'}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className={`telemetry-card stage-guidance stage-guidance-${purchaseStage.toLowerCase()}`}>
          <p className="telemetry-kicker">{purchaseStage === 'ALREADY_BOUGHT' ? 'POST-PURCHASE SAFETY' : 'PRE-PURCHASE GUIDANCE'}</p>
          <strong>{purchaseStage === 'ALREADY_BOUGHT' ? 'Already bought' : 'Before buying'}</strong>
          <p>{recommendation}</p>
          <small>This is precautionary guidance, not a product-authenticity verdict or medical advice.</small>
        </section>
        <footer className="page-footer"><span>CheckAm RESULT · {scanId}</span><span>Completed {completedAt ? new Date(completedAt).toLocaleTimeString() : 'just now'}</span></footer>
      </div>
    </main>
  )
}

export default ResultPage
