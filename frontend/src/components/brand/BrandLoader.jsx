import logo from '../../public/logo-trim.png'

// Check Am loading mark: the logo with a soft pulse and a spinning ring.
// variant="overlay" covers the screen; variant="inline" sits inside a page.
function BrandLoader({ label = 'Loading…', sublabel = '', variant = 'inline' }) {
  return (
    <div className={`brand-loader brand-loader-${variant}`} role="status" aria-live="polite">
      <div className="brand-loader-mark">
        <span className="brand-loader-ring" aria-hidden="true" />
        <img src={logo} alt="Check Am" />
      </div>
      <p className="brand-loader-label">{label}</p>
      {sublabel && <p className="brand-loader-sub">{sublabel}</p>}
    </div>
  )
}

export default BrandLoader
