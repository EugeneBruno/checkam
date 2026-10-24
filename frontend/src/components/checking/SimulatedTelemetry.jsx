function SimulatedTelemetry({ elapsed, running, live }) {
  const time = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`

  return (
    <section className="telemetry-card runtime-card" aria-label="Agent runtime telemetry">
      <div className="runtime-top">
        <div><span className={`runtime-indicator ${running ? 'runtime-on' : ''}`} /><span>{live ? 'AGENT CONNECTION' : 'SIMULATED RUNTIME'}</span></div>
        <time>{time}</time>
      </div>
      <div className={`runtime-wave ${running ? 'wave-running' : ''}`} aria-hidden="true">
        {[16, 24, 12, 32, 20, 39, 25, 14, 29, 42, 18, 34, 22, 12, 28, 38, 17, 25, 11, 33, 20, 39, 16, 29, 13, 35, 22, 16, 31, 20, 37, 14, 26, 40, 18, 29, 12, 24, 34, 17].map((height, index) => (
          <i key={index} style={{ '--bar-height': `${height}px`, '--bar-delay': `${index * 24}ms` }} />
        ))}
      </div>
      <div className="runtime-foot"><span>{live ? 'Receiving agent events' : 'Event stream preview'}</span><span>{running ? 'STREAMING' : 'IDLE'}</span></div>
    </section>
  )
}

export default SimulatedTelemetry