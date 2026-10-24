import { useState } from 'react'

const DEMO_PRESETS = [
  {
    id: 'genuine-drug',
    label: 'Genuine Drug',
    product: {
      productName: 'Amartem Soft Gel',
      brand: 'Amatem Pharmaceuticals',
      category: 'Medicine',
      variant: 'Soft Gel',
      nafdacNumber: 'A4-0321',
      batchNumber: 'BN-88412',
      expiryDate: '12/2026',
    },
    situation: 'BEFORE_BUYING',
    summary: 'Check this Amartem Soft Gel pack before purchase. Packaging details and identifiers appear consistent in this sample.',
    outcome: 'Likely genuine indicators',
    simulation: 'Sample data only: no registry lookup was performed.',
    checks: [
      { id: 'preset-registry', name: 'NAFDAC identifier', status: 'passed', detail: 'Sample identifier matches this fixture; not checked against a live registry.' },
      { id: 'preset-batch', name: 'Batch consistency', status: 'passed', detail: 'No duplicate-batch anomaly is configured in this fixture.' },
      { id: 'preset-packaging', name: 'Packaging signals', status: 'passed', detail: 'No packaging anomaly is configured in this fixture.' },
    ],
  },
  {
    id: 'registry-mismatch',
    label: 'Registry Mismatch',
    product: {
      productName: 'Betaclox 500mg',
      brand: 'Betaclox',
      category: 'Medicine',
      variant: '500mg',
      nafdacNumber: '04-2191-ERR',
      batchNumber: 'BN-10293',
      expiryDate: '08/2025',
    },
    situation: 'BEFORE_BUYING',
    summary: 'Check the Betaclox 500mg sample: its NAFDAC identifier is deliberately marked invalid in this demo fixture.',
    outcome: 'Registry mismatch simulated',
    simulation: 'Invalid/revoked credential is a scripted demo result, not a live NAFDAC registry check.',
    checks: [
      { id: 'preset-registry', name: 'NAFDAC identifier', status: 'failed', detail: 'Fixture marks this identifier invalid/revoked; no live registry was queried.' },
      { id: 'preset-product-match', name: 'Product-to-registration match', status: 'failed', detail: 'The fixture is configured as a registry mismatch edge case.' },
    ],
  },
  {
    id: 'batch-clone',
    label: 'Batch Clone',
    product: {
      productName: 'Emzor Paracetamol',
      brand: 'Emzor',
      category: 'Medicine',
      variant: 'Paracetamol',
      nafdacNumber: '04-0123',
      batchNumber: 'BN-KANO-99',
      expiryDate: '01/2026',
    },
    situation: 'ALREADY_BOUGHT',
    summary: 'Review this Emzor Paracetamol sample for a possible duplicate batch reported at a different location.',
    outcome: 'Duplicate batch anomaly simulated',
    simulation: 'Duplicate-location evidence is scripted sample data, not a live report.',
    checks: [
      { id: 'preset-registry', name: 'NAFDAC identifier', status: 'passed', detail: 'The sample registration is configured as valid in this fixture; not checked against a live registry.' },
      { id: 'preset-batch', name: 'Batch-location consistency', status: 'failed', detail: 'Fixture simulates the same batch appearing at a different location.' },
    ],
  },
  {
    id: 'community-reported',
    label: 'Community Reported',
    product: {
      productName: 'Lonart DS',
      brand: 'Lonart',
      category: 'Medicine',
      variant: 'DS',
      nafdacNumber: 'A4-9981',
      batchNumber: 'BN-TF-441',
      expiryDate: '04/2025',
      seller: 'Trade Fair market',
    },
    situation: 'BEFORE_BUYING',
    summary: 'Review this Lonart DS sample with a simulated community alert associated with Trade Fair market reports.',
    outcome: 'Community report simulated',
    simulation: 'Trade Fair report is a scripted sample, not a verified active market report.',
    checks: [
      { id: 'preset-community', name: 'Community report signal', status: 'warning', detail: 'Fixture includes a simulated Trade Fair market report; this is not a verified real-world report.' },
      { id: 'preset-batch', name: 'Batch identifier', status: 'warning', detail: 'Use the batch number as a lead for independent verification.' },
    ],
  },
  {
    id: 'son-regulated',
    label: 'SON Regulated',
    product: {
      productName: 'Coleman 2.5mm Wire',
      brand: 'Coleman',
      category: 'Electrical cable',
      variant: '2.5mm',
      sonNumber: 'SON-CAP-8812',
      batchNumber: 'BN-COL-112',
    },
    situation: 'BEFORE_BUYING',
    summary: 'Check this Coleman 2.5mm wire sample using a non-pharmaceutical SON certification schema.',
    outcome: 'SON schema sample',
    simulation: 'SON validation is a scripted fixture; no live certification database was queried.',
    checks: [
      { id: 'preset-schema', name: 'Product category schema', status: 'passed', detail: 'Non-pharmaceutical product routes to the SON identifier field in this fixture.' },
      { id: 'preset-son', name: 'SON certification identifier', status: 'warning', detail: 'Identifier is present in sample input but not verified against a live database.' },
    ],
  },
  {
    id: 'unknown-item',
    label: 'Unknown Item',
    product: {
      productName: 'Bio-Glow Cream',
      brand: 'Bio-Glow',
      category: 'Cosmetics',
      variant: 'Cream',
      nafdacNumber: 'UNVERIFIED',
      batchNumber: 'BN-BIO-009',
      expiryDate: '11/2025',
    },
    situation: 'ALREADY_BOUGHT',
    summary: 'Review this uncataloged Bio-Glow Cream sample; live external research is unavailable in this demo.',
    outcome: 'Unknown catalog item',
    simulation: 'Would request external reference research if a research service were connected. No scraping or external lookup runs here.',
    checks: [
      { id: 'preset-catalog', name: 'Catalog match', status: 'warning', detail: 'No catalog match is configured in this fixture.' },
      { id: 'preset-external', name: 'External reference research', status: 'warning', detail: 'Not run: this app has no connected web research service.' },
    ],
  },
]

function DemoPresetToolbar({ onSelect }) {
  const [open, setOpen] = useState(false)

  function selectPreset(preset) {
    onSelect({
      id: `scan-${preset.id}`,
      preset: {
        id: preset.id,
        label: preset.label,
        outcome: preset.outcome,
        simulation: preset.simulation,
        checks: preset.checks,
      },
      product: preset.product,
      situation: {
        intent: preset.situation,
        summary: preset.summary,
        location: preset.id === 'community-reported' ? 'Trade Fair market' : '',
        urgency: preset.id === 'community-reported' || preset.id === 'unknown-item' ? 'soon' : 'routine',
        peopleInvolved: '',
        safeToApproach: '',
        additionalDetails: preset.simulation,
      },
      attachments: [],
    })
    setOpen(false)
  }

  return (
    <aside className={`demo-preset-tray ${open ? 'demo-preset-tray-open' : ''}`}>
      {open && <div className="demo-preset-panel" aria-label="Judge demo presets">
        <div className="demo-preset-panel-heading">
          <div><small>JUDGE MODE</small><strong>Scenario presets</strong></div>
          <button type="button" aria-label="Close demo presets" onClick={() => setOpen(false)}>×</button>
        </div>
        <p>Loads a deterministic sample and opens its review trace. No live registry, report, or web lookups are performed.</p>
        <div className="demo-preset-list">
          {DEMO_PRESETS.map((preset, index) => (
            <button className="demo-preset-option" key={preset.id} type="button" onClick={() => selectPreset(preset)}>
              <span className="demo-preset-index">{String(index + 1).padStart(2, '0')}</span>
              <span><strong>{preset.label}</strong><small>{preset.outcome}</small></span>
              <span className="demo-preset-arrow">→</span>
            </button>
          ))}
        </div>
      </div>}
      <button className="demo-preset-trigger" type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span aria-hidden="true">⚙</span> Demo presets <i>{open ? '−' : '+'}</i>
      </button>
    </aside>
  )
}

export default DemoPresetToolbar