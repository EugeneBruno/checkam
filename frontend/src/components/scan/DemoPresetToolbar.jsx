import { useState } from 'react'

// Judge presets: real checks sent to the Check Am API with typed details (no photo needed).
// Numbers come from our demo data (data/greenbook_sample.json, known_fakes.json, DEMO- scan history).
const DEMO_PRESETS = [
  {
    id: 'napams-confirmed',
    label: 'Confirmed on NAPAMS',
    product: { productName: 'Apple Drink', brand: 'La Casera', category: 'drink', nafdacNumber: '01-4278', barcode: '5060626030008' },
    situation: 'BEFORE_BUYING',
    outcome: 'Expect: registry match from a NAPAMS confirmation',
    simulation: 'Real check. 01-4278 was confirmed on NAPAMS by a person (napams_assist.py).',
  },
  {
    id: 'registry-mismatch',
    label: 'Number belongs to another product',
    product: { productName: 'Shea Butter Cream', brand: 'Glow', category: 'cosmetic', nafdacNumber: 'A3-100882' },
    situation: 'BEFORE_BUYING',
    outcome: 'Expect: likely fake (registry mismatch)',
    simulation: 'Real check. A3-100882 is registered to a different product in the Greenbook data.',
  },
  {
    id: 'batch-clone',
    label: 'Cloned batch number',
    product: { productName: 'Always 3-in-1 Maxi Thick', brand: 'Always', category: 'medical device', nafdacNumber: '03-2099', batchNumber: 'DEMO-AL5531', expiryDate: '2028-09' },
    situation: 'ALREADY_BOUGHT',
    outcome: 'Expect: likely fake (same batch, different expiry)',
    simulation: 'Real check against the DEMO- scan history: this batch was seen elsewhere with another expiry.',
  },
  {
    id: 'nafdac-alert',
    label: 'NAFDAC alert',
    product: { productName: 'Betaclox Ampicillin Cloxacillin', brand: 'Betaclox', category: 'medicine', nafdacNumber: 'A4-4724', batchNumber: '230701', expiryDate: '07/2026' },
    situation: 'BEFORE_BUYING',
    outcome: 'Expect: likely fake (matches a NAFDAC counterfeit alert)',
    simulation: 'Real check against the NAFDAC alerts we load (known_fakes.json).',
  },
  {
    id: 'phone-imei',
    label: 'Phone: box ≠ phone',
    product: { productName: '3110 Classic', brand: 'Nokia', category: 'phone', imei: '490154203237518', imeiDevice: '356938035643809' },
    situation: 'BEFORE_BUYING',
    outcome: 'Expect: likely fake (IMEI on box differs from *#06#)',
    simulation: 'Real check. The box IMEI and the phone’s *#06# IMEI don’t match.',
  },
  {
    id: 'research',
    label: 'Not in our data → research',
    product: { productName: 'Texas BBQ Sauce', brand: 'Pringles', category: 'food', barcode: '5053990161966' },
    situation: 'BEFORE_BUYING',
    outcome: 'Expect: online research with sources (15–20s the first time)',
    simulation: 'Real check. Food isn’t in our Greenbook copy, so Check Am researches it online.',
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
      },
      product: preset.product,
      situation: {
        intent: preset.situation,
        summary: `${preset.product.brand} ${preset.product.productName}`,
        location: '',
        urgency: 'routine',
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
        <p>Runs a real check with typed details, no photo needed. Same server, same rules as a photo scan.</p>
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
        Demo presets <i>{open ? '−' : '+'}</i>
      </button>
    </aside>
  )
}

export default DemoPresetToolbar