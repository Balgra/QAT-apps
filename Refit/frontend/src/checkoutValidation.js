export const POSTAL_FORMATS = {
  SE: [/^[0-9]{3} ?[0-9]{2}$/, 'Use five digits, for example 41257 or 412 57.'],
  DK: [/^[0-9]{4}$/, 'Use four digits for a Danish postal code.'],
  NO: [/^[0-9]{4}$/, 'Use four digits for a Norwegian postal code.'],
  FI: [/^[0-9]{5}$/, 'Use five digits for a Finnish postal code.'],
  DE: [/^[0-9]{5}$/, 'Use five digits for a German postal code.'],
  FR: [/^[0-9]{5}$/, 'Use five digits for a French postal code.'],
  US: [/^[0-9]{5}(-[0-9]{4})?$/, 'Use a ZIP code such as 10001 or 10001-1234.'],
}

export function validateDelivery(form) {
  const errors = {}
  const name = form.customer_name.trim()
  const address = form.address.trim()
  const city = form.city.trim()
  const country = form.country.trim().toUpperCase()
  const postal = form.postal_code.trim()
  if (name.length < 2 || name.length > 80 || !/\p{L}/u.test(name)) {
    errors.customer_name = 'Enter your name using 2–80 characters, including letters.'
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = 'Enter a valid email address, for example name@example.com.'
  }
  if (address.length < 5 || address.length > 180 || !/\p{L}/u.test(address) || !/[0-9]/.test(address)) {
    errors.address = 'Enter a street or PO box address with a number, for example Example Street 12.'
  }
  if (city.length < 2 || city.length > 80 || !/\p{L}/u.test(city)) {
    errors.city = 'Enter a city name using 2–80 characters, including letters.'
  }
  const format = POSTAL_FORMATS[country]
  if (!format) errors.country = 'Use a supported country code: SE, DK, FI, NO, DE, FR or US.'
  if (!postal || (format && !format[0].test(postal)) || (!format && !/[0-9]/.test(postal))) {
    errors.postal_code = format?.[1] || 'Enter a postal code containing digits for the selected country.'
  }
  return errors
}

export function validatePayment(form, now = new Date()) {
  const errors = {}
  const number = form.card_number.replace(/[ -]/g, '')
  if (!/^[0-9]{13,19}$/.test(number)) errors.card_number = 'Enter a demonstration card number with 13–19 digits.'
  if (!/^(0[1-9]|1[0-2])\/[0-9]{2}$/.test(form.expiry)) {
    errors.expiry = 'Enter expiry as MM/YY, for example 12/35.'
  } else {
    const [month, year] = form.expiry.split('/').map(Number)
    if (2000 + year < now.getUTCFullYear() || (2000 + year === now.getUTCFullYear() && month < now.getUTCMonth() + 1)) {
      errors.expiry = 'The demonstration card has expired. Enter a current or future expiry month.'
    }
  }
  if (!/^[0-9]{3,4}$/.test(form.cvv)) errors.cvv = 'Enter a CVV containing three or four digits.'
  if (form.coupon_code.length > 24) errors.coupon_code = 'Coupon codes can contain at most 24 characters.'
  return errors
}
