function AgentThoughtLog({ events, live }) {
  return (
    <section className="telemetry-card trace-card trace-terminal" aria-labelledby="trace-heading">
      <div className="telemetry-heading">
        <div>
          <p className="telemetry-kicker">ACTIVITY</p>
          <h2 id="trace-heading">What Check Am is doing</h2>
        </div>
        <span className={`feed-badge ${live ? 'feed-live' : 'feed-demo'}`}>
          <i /> {live ? 'LIVE' : 'DEMO'}
        </span>
      </div>
      {events.length === 0
        ? <div className="trace-empty">Starting…</div>
        : <ol className="trace-list" aria-live="polite">
          {events.map((event, index) => (
            <li className={`trace-event ${index === events.length - 1 ? 'trace-current' : ''}`} key={event.id}>
              <span className={`trace-marker trace-${event.kind}`} aria-hidden="true">{event.kind === 'verification' ? '✓' : '·'}</span>
              <div className="trace-event-body">
                <div className="trace-event-top">
                  <strong>{event.title}</strong>
                  <time>{event.time}</time>
                </div>
                <p>{event.detail}</p>
                {event.status && <span className={`trace-status trace-status-${event.status}`}>{event.status}</span>}
              </div>
            </li>
          ))}
        </ol>}
    </section>
  )
}

export default AgentThoughtLog