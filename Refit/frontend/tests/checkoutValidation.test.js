import test from 'node:test'
import assert from 'node:assert/strict'
import { validateDelivery, validatePayment } from '../src/checkoutValidation.js'

const valid = {
  customer_name: 'Åsa O’Neill', email: 'asa@example.com', address: 'Example Street 12', city: 'Göteborg',
  postal_code: '41257', country: 'SE', card_number: '4242 4242 4242 4242', expiry: '12/35', cvv: '123', coupon_code: '',
}

test('all-a delivery provides every field error rather than silently submitting', () => {
  const errors = validateDelivery({ ...valid, customer_name: 'a', email: 'a', address: 'aaaaa', city: 'a', postal_code: 'aaaaa', country: 'aa' })
  assert.deepEqual(Object.keys(errors).sort(), ['customer_name', 'email', 'address', 'city', 'postal_code', 'country'].sort())
})

test('valid international names, trimmed values, street addresses and PO boxes are accepted', () => {
  assert.deepEqual(validateDelivery(valid), {})
  assert.deepEqual(validateDelivery({ ...valid, customer_name: ' Åsa ', address: ' PO Box 12 ', country: ' se ', postal_code: ' 412 57 ' }), {})
})

for (const [country, good, bad] of [['SE', '412 57', 'aaaaa'], ['DK', '1234', '12345'], ['NO', '0123', '123'],
  ['FI', '00100', '0010'], ['DE', '10115', 'ABCDE'], ['FR', '75001', '7500'], ['US', '10001-1234', '10001-123']]) {
  test(`${country} postal format is validated`, () => {
    assert.deepEqual(validateDelivery({ ...valid, country, postal_code: good }), {})
    assert.ok(validateDelivery({ ...valid, country, postal_code: bad }).postal_code)
  })
}

test('whitespace and numeric-only delivery text are rejected', () => {
  for (const name of ['customer_name', 'address', 'city']) {
    assert.ok(validateDelivery({ ...valid, [name]: '    ' })[name])
    assert.ok(validateDelivery({ ...valid, [name]: '12345' })[name])
  }
})

test('delivery length boundaries do not accept oversized fields', () => {
  for (const [name, maximum] of [['customer_name', 80], ['city', 80], ['address', 180]]) {
    const value = name === 'address' ? 'a'.repeat(maximum - 1) + '1' : 'a'.repeat(maximum)
    assert.equal(validateDelivery({ ...valid, [name]: value })[name], undefined)
    assert.ok(validateDelivery({ ...valid, [name]: value + 'a' })[name])
  }
})

test('payment errors remain visible with native validation disabled', () => {
  const now = new Date('2026-10-29T12:00:00Z')
  assert.deepEqual(validatePayment(valid, now), {})
  assert.deepEqual(Object.keys(validatePayment({ ...valid, card_number: 'a', expiry: 'a', cvv: 'a' }, now)).sort(), ['card_number', 'expiry', 'cvv'].sort())
  assert.ok(validatePayment({ ...valid, expiry: '09/26' }, now).expiry)
  assert.equal(validatePayment({ ...valid, expiry: '10/26' }, now).expiry, undefined)
})
