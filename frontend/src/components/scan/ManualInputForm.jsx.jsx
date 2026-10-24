const fields = [
  { name: 'productName', label: 'Product name', placeholder: 'Name printed on the item', autocomplete: 'off' },
  { name: 'brand', label: 'Brand', placeholder: 'Brand or manufacturer', autocomplete: 'organization' },
  { name: 'category', label: 'Category', placeholder: 'e.g. medicine, skincare, fashion' },
  { name: 'variant', label: 'Model / variant', placeholder: 'Strength, size, colour, or model' },
  { name: 'barcode', label: 'Barcode', placeholder: 'Enter digits as printed', inputMode: 'numeric' },
  { name: 'nafdacNumber', label: 'NAFDAC number', placeholder: 'If shown on the package' },
  { name: 'sonNumber', label: 'SON / certification mark', placeholder: 'Standard or certification number' },
  { name: 'batchNumber', label: 'Batch / lot number', placeholder: 'If available' },
  { name: 'manufactureDate', label: 'Manufacture date', type: 'text', placeholder: 'e.g. 03/2025' },
  { name: 'expiryDate', label: 'Expiry date', type: 'text', placeholder: 'e.g. 03/2027' },
  { name: 'price', label: 'Listed price', placeholder: 'Optional price and currency', inputMode: 'decimal' },
  { name: 'seller', label: 'Seller / shop', placeholder: 'Optional seller name' },
]

function ManualInputForm({ values, onChange }) {
  function updateField(event) {
    const { name, value } = event.target
    onChange({ ...values, [name]: value })
  }

  return (
    <details className="manual-input-panel">
      <summary>
        <span className="manual-summary-icon" aria-hidden="true">≡</span>
        <span className="manual-summary-copy">
          <strong>Enter product details manually</strong>
          <small>Useful with slow data, unreadable labels, or damaged packaging</small>
        </span>
        <span className="manual-summary-toggle" aria-hidden="true">+</span>
      </summary>
      <div className="manual-input-content">
        <p className="manual-input-note">Add anything you can read. Leave unknown details blank; these fields are optional and won’t be treated as verified facts.</p>
        <div className="manual-input-grid">
          {fields.map(({ name, label, placeholder, type = 'text', inputMode, autocomplete }) => (
            <label className="manual-field" htmlFor={`manual-${name}`} key={name}>
              <span>{label}</span>
              <input
                autoComplete={autocomplete || 'off'}
                id={`manual-${name}`}
                inputMode={inputMode}
                maxLength={160}
                name={name}
                onChange={updateField}
                placeholder={placeholder}
                type={type}
                value={values[name] || ''}
              />
            </label>
          ))}
        </div>
      </div>
    </details>
  )
}

export default ManualInputForm