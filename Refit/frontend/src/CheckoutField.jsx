export default function CheckoutField({ name, label, form, errors, onChange, onBlur, wide = false, ...inputProps }) {
  const id = `checkout-${name}`
  const error = errors[name]
  return <div className={`checkout-field${wide ? ' wide' : ''}`}>
    <label htmlFor={id}>{label}</label>
    <input {...inputProps} id={id} name={name} value={form[name]} onChange={onChange} onBlur={onBlur}
      aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} />
    {error && <span id={`${id}-error`} className="field-error">{error}</span>}
  </div>
}
