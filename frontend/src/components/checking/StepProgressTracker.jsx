function StepProgressTracker({ steps, activeIndex, status }) {
  const progress = steps.length === 0
    ? 0
    : status === 'completed'
    ? 100
    : Math.max(3, ((activeIndex + 1) / steps.length) * 100)

  return (
    <section className="telemetry-card progress-card" aria-labelledby="progress-heading">
      <div className="telemetry-heading">
        <div>
          <p className="telemetry-kicker">RESEARCH PIPELINE</p>
          <h2 id="progress-heading">Run progress</h2>
        </div>
        <span className="progress-count">{Math.min(activeIndex + 1, steps.length)} <i>/</i> {steps.length}</span>
      </div>
      <div className="progress-track" aria-label={`${Math.round(progress)}% complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol className="pipeline-list">
        {steps.map((step, index) => {
          const stepStatus = index < activeIndex || status === 'completed'
            ? 'done'
            : index === activeIndex && status === 'running'
              ? 'active'
              : index === activeIndex && status === 'paused'
                ? 'paused'
                : 'waiting'
          return (
            <li className={`pipeline-step pipeline-${stepStatus}`} key={step.id}>
              <span className="pipeline-marker">{stepStatus === 'done' ? '✓' : String(index + 1).padStart(2, '0')}</span>
              <div><strong>{step.label}</strong><small>{step.description}</small></div>
              {stepStatus === 'active' && <span className="pipeline-active-label">IN PROGRESS</span>}
              {stepStatus === 'done' && <span className="pipeline-done-label">DONE</span>}
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default StepProgressTracker