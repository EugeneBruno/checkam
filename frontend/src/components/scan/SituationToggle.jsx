const situations = [
  {
    value: 'BEFORE_BUYING',
    label: 'Before buying',
    description: 'Pre-purchase validation',
  },
  {
    value: 'ALREADY_BOUGHT',
    label: 'Already bought',
    description: 'Post-purchase safety check',
  },
]

function SituationToggle({ value, onChange }) {
  return (
    <fieldset className="situation-toggle-field">
      <legend className="field-label">When are you checking this item?</legend>
      <p className="situation-toggle-hint">This changes the guidance shown with the result.</p>
      <div className="situation-toggle" role="group" aria-label="Purchase situation">
        {situations.map((situation) => (
          <button
            aria-pressed={value === situation.value}
            className={`situation-toggle-option ${value === situation.value ? 'situation-toggle-active' : ''}`}
            key={situation.value}
            onClick={() => onChange(situation.value)}
            type="button"
          >
            <span className="situation-option-title">{situation.label}</span>
            <span className="situation-option-description">{situation.description}</span>
          </button>
        ))}
      </div>
    </fieldset>
  )
}

export default SituationToggle