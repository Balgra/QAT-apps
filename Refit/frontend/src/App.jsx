import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, Check, Minus, Plus, Search, ShoppingBag, Sparkles, X } from 'lucide-react'
import Operations from './Operations'
import { request, API_URL } from './api'
import CheckoutField from './CheckoutField'
import { validateDelivery, validatePayment } from './checkoutValidation'

const categories = ['all', 'tops', 'bottoms', 'outerwear', 'dresses', 'shoes', 'accessories']
const categoryMarks = { tops: 'T', bottoms: 'B', outerwear: 'O', dresses: 'D', shoes: 'S', accessories: 'A' }
const colorMap = {
  Camel: '#b99367', Cream: '#e7dfcf', Indigo: '#425273', Forest: '#496650', Burgundy: '#733b49',
  'Off-white': '#dedbd2', Terracotta: '#b76f51', Sage: '#9eaa8e', Black: '#32312f', Sky: '#8eb2c0',
  Rust: '#a75b3c', Navy: '#34445e', Floral: '#aa7888', Cobalt: '#3c5e94', Chocolate: '#6c4c3d',
  Oat: '#c9b99e', Moss: '#657358', Stone: '#9a9185', 'Mid blue': '#657d96', Cognac: '#a66d3d',
}

function ProductArtwork({ product }) {
  const base = colorMap[product.color] || '#7f8f7b'
  return (
    <div className="product-art" style={{ '--product-color': base }} aria-hidden="true">
      <div className={`garment garment-${product.category}`}>
        <span>{categoryMarks[product.category]}</span>
      </div>
      <small>{product.color}</small>
    </div>
  )
}

function CartDrawer({ cart, products, onClose, onQuantity, onCheckout }) {
  const lines = cart.map(item => ({ ...item, product: products.find(p => p.id === item.productId) })).filter(x => x.product)
  const subtotal = lines.reduce((sum, line) => sum + line.product.price * line.quantity, 0)
  return (
    <div className="drawer-layer" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}>
      <aside className="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="cart-title">
        <div className="drawer-head">
          <div><span className="eyebrow">Your edit</span><h2 id="cart-title">Shopping bag</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close bag"><X /></button>
        </div>
        {lines.length === 0 ? (
          <div className="empty-state"><ShoppingBag /><h3>Your bag is taking a breather.</h3><p>Add a piece that deserves another life.</p></div>
        ) : (
          <>
            <div className="cart-lines">
              {lines.map(({ product, quantity }) => (
                <article className="cart-line" key={product.id}>
                  <ProductArtwork product={product} />
                  <div className="cart-line-copy">
                    <h3>{product.name}</h3><p>{product.size} · {product.condition}</p>
                    <div className="quantity-control">
                      <button onClick={() => onQuantity(product.id, quantity - 1)} aria-label={`Remove one ${product.name}`}><Minus /></button>
                      <span>{quantity}</span>
                      <button onClick={() => onQuantity(product.id, quantity + 1)} disabled={quantity >= product.stock} aria-label={`Add one ${product.name}`}><Plus /></button>
                    </div>
                  </div>
                  <strong>€{(product.price * quantity).toFixed(2)}</strong>
                </article>
              ))}
            </div>
            <div className="drawer-total"><span>Estimated subtotal</span><strong>€{subtotal.toFixed(2)}</strong></div>
            <p className="fine-print">Delivery, discounts and tax are calculated at checkout.</p>
            <button className="primary-button full" onClick={onCheckout}>Proceed to checkout <ArrowRight /></button>
          </>
        )}
      </aside>
    </div>
  )
}

function Checkout({ cart, products, onBack, onComplete }) {
  const [form, setForm] = useState({ customer_name: '', email: '', address: '', city: '', postal_code: '', country: 'SE', card_number: '4242 4242 4242 4242', expiry: '12/30', cvv: '123', shipping_method: 'standard', coupon_code: '', gift_wrap: false })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [quote, setQuote] = useState(null)
  const [reservation, setReservation] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const formRef = useRef(null)
  const summaryRef = useRef(null)
  const hasFieldErrors = Object.values(fieldErrors).some(Boolean)
  useEffect(() => {
    if (error && !hasFieldErrors) summaryRef.current?.focus()
  }, [error, hasFieldErrors])
  const subtotal = cart.reduce((sum, item) => sum + (products.find(p => p.id === item.productId)?.price || 0) * item.quantity, 0)
  const update = event => {
    const { name, value, type, checked } = event.target
    const next = { ...form, [name]: type === 'checkbox' ? checked : value }
    setForm(next)
    const updatedErrors = { ...validateDelivery(next), ...validatePayment(next) }
    setFieldErrors(current => Object.fromEntries(Object.keys(current).filter(key => updatedErrors[key]).map(key => [key, updatedErrors[key]])))
    setError('')
    setQuote(null)
  }
  const validate = errors => {
    setFieldErrors(errors)
    const first = Object.keys(errors)[0]
    if (first) {
      setError('Please correct the highlighted fields before continuing.')
      formRef.current?.elements.namedItem(first)?.focus()
      return false
    }
    return true
  }
  const failed = reason => {
    setError(reason.message)
    setFieldErrors(reason.fieldErrors || {})
    const first = Object.keys(reason.fieldErrors || {})[0]
    if (first) formRef.current?.elements.namedItem(first)?.focus()
  }
  const blur = event => {
    const name = event.target.name
    const errors = { ...validateDelivery(form), ...validatePayment(form) }
    setFieldErrors(current => ({ ...current, [name]: errors[name] }))
  }
  const field = (name, label, props = {}) => <CheckoutField name={name} label={label} form={form} errors={fieldErrors} onChange={update} onBlur={blur} {...props} />
  const payload = () => ({ ...form, customer_name: form.customer_name.trim(), email: form.email.trim(), address: form.address.trim(), city: form.city.trim(), postal_code: form.postal_code.trim(), country: form.country.trim().toUpperCase(), coupon_code: form.coupon_code || null, reservation_id: reservation?.reservation_id || null, items: cart.map(item => ({ product_id: item.productId, quantity: item.quantity })) })
  const review = async () => {
    if (!validate(validateDelivery(form))) return
    setBusy(true); setError('')
    try { setQuote(await request('/quote', { method: 'POST', body: payload() })) }
    catch (reason) { failed(reason) } finally { setBusy(false) }
  }
  const reserve = async () => {
    const { email } = validateDelivery(form)
    if (!validate(email ? { email } : {})) return
    setBusy(true); setError('')
    try { setReservation(await request('/reservations', { method: 'POST', body: { items: payload().items, email: form.email.trim() } })) }
    catch (reason) { failed(reason) } finally { setBusy(false) }
  }
  const release = async () => {
    setBusy(true); setError('')
    try { await request(`/reservations/${reservation.reservation_id}`, { method: 'DELETE' }); setReservation(null); setQuote(null) }
    catch (reason) { setError(reason.message) } finally { setBusy(false) }
  }
  const submit = async event => {
    event.preventDefault()
    if (!validate({ ...validateDelivery(form), ...validatePayment(form) })) return
    setBusy(true); setError('')
    try {
      const data = await request('/checkout', { method: 'POST', body: payload() })
      localStorage.setItem('refit-order', data.order_id)
      onComplete(data)
    } catch (reason) { failed(reason) } finally { setBusy(false) }
  }
  return (
    <main className="checkout-page">
      <button className="text-button" onClick={onBack}>← Back to shop</button>
      <div className="checkout-grid">
        <form ref={formRef} className="checkout-form" onSubmit={submit} noValidate>
          <span className="eyebrow">Secure demonstration checkout</span><h1>Almost yours.</h1>
          {error && <p ref={summaryRef} className="error-message" role="alert" tabIndex={-1}>{error}</p>}
          <section><h2>Delivery details</h2><div className="form-grid">
            {field('customer_name', 'Full name', { required: true, wide: true, autoComplete: 'name' })}
            {field('email', 'Email', { required: true, wide: true, type: 'email', autoComplete: 'email' })}
            {field('address', 'Address', { required: true, wide: true, autoComplete: 'street-address' })}
            {field('city', 'City', { required: true, autoComplete: 'address-level2' })}
            {field('postal_code', 'Postal code', { required: true, autoComplete: 'postal-code' })}
            {field('country', 'Country code', { required: true, maxLength: 2, autoComplete: 'country' })}
          </div></section>
          <section><h2>Delivery method</h2><div className="shipping-options">
            {[['standard', 'Standard', '3–5 weekdays'], ['express', 'Express', '1–2 weekdays'], ['pickup', 'Pickup', 'From our studio']].map(([value, title, note]) => <label className={form.shipping_method === value ? 'selected' : ''} key={value}><input type="radio" name="shipping_method" value={value} checked={form.shipping_method === value} onChange={update} /><strong>{title}</strong><span>{note}</span></label>)}
          </div></section>
          <section><h2>Payment</h2><div className="form-grid">
            {field('card_number', 'Card number', { required: true, wide: true, inputMode: 'numeric', autoComplete: 'cc-number' })}
            {field('expiry', 'Expiry', { required: true, placeholder: 'MM/YY', autoComplete: 'cc-exp' })}
            {field('cvv', 'CVV', { required: true, inputMode: 'numeric', autoComplete: 'cc-csc' })}
            {field('coupon_code', 'Coupon (optional)', { wide: true, placeholder: 'Try WELCOME10' })}
            <label className="check wide"><input type="checkbox" name="gift_wrap" checked={form.gift_wrap} onChange={update} /> Wrap this order as a gift</label>
          </div></section>
          <div className="operation-actions">
            <button type="button" disabled={busy} onClick={review}>Review final total</button>
            {reservation ? <button type="button" disabled={busy} onClick={release}>Release hold</button> : <button type="button" disabled={busy || !form.email} onClick={reserve}>Hold these pieces for 10 minutes</button>}
          </div>
          {reservation && <p>Held until {new Date(reservation.expires_at).toLocaleTimeString()}. Keep the same email for this hold.</p>}
          {quote && <section aria-live="polite"><h2>Total €{quote.totals.total.toFixed(2)}</h2><p>Discount €{quote.totals.discount.toFixed(2)} · delivery €{quote.totals.shipping.toFixed(2)} · tax €{quote.totals.tax.toFixed(2)} · gift wrap €{quote.totals.gift_wrap.toFixed(2)}</p><ul>{quote.messages.map(message => <li key={message}>{message}</li>)}</ul></section>}
          <button type="submit" className="primary-button full" disabled={busy}>{busy ? 'Placing your order…' : 'Buy now'} <ArrowRight /></button>
        </form>
        <aside className="order-card"><span className="eyebrow">Order summary</span><h2>{cart.reduce((n, x) => n + x.quantity, 0)} pieces</h2>{cart.map(item => { const p = products.find(product => product.id === item.productId); return p ? <div className="summary-line" key={p.id}><span>{item.quantity} × {p.name}</span><strong>€{(p.price * item.quantity).toFixed(2)}</strong></div> : null })}<div className="summary-total"><span>Subtotal</span><strong>€{subtotal.toFixed(2)}</strong></div><p>Final shipping, discounts and tax are shown on your confirmation.</p></aside>
      </div>
    </main>
  )
}

function Success({ order, onContinue }) {
  return <main className="success-page"><div className="success-mark"><Check /></div><span className="eyebrow">Order {order.order_id}</span><h1>Thank you.</h1><p>{order.message}</p><div className="receipt"><span>{order.item_count} pieces</span><strong>€{order.totals.total.toFixed(2)}</strong></div><button className="primary-button" onClick={onContinue}>Continue browsing <ArrowRight /></button></main>
}

export default function App() {
  const [products, setProducts] = useState([])
  const [status, setStatus] = useState('loading')
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [cart, setCart] = useState([])
  const [drawer, setDrawer] = useState(false)
  const [page, setPage] = useState('shop')
  const [order, setOrder] = useState(null)
  const refreshProducts = () => request('/products').then(setProducts).catch(() => setStatus('error'))

  useEffect(() => { fetch(`${API_URL}/products`).then(response => { if (!response.ok) throw new Error(); return response.json() }).then(data => { setProducts(data); setStatus('ready') }).catch(() => setStatus('error')) }, [])
  const visible = useMemo(() => products.filter(product => (category === 'all' || product.category === category) && (!query || `${product.name} ${product.description} ${product.seller}`.toLowerCase().includes(query.toLowerCase()))), [products, category, query])
  const count = cart.reduce((sum, item) => sum + item.quantity, 0)
  const add = product => { setCart(current => { const found = current.find(item => item.productId === product.id); return found ? current.map(item => item.productId === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) } : item) : [...current, { productId: product.id, quantity: 1 }] }); setDrawer(true) }
  const quantity = (productId, value) => setCart(current => value < 1 ? current.filter(item => item.productId !== productId) : current.map(item => item.productId === productId ? { ...item, quantity: value } : item))
  const complete = data => { setOrder(data); setCart([]); setPage('success'); window.scrollTo(0, 0) }
  if (page === 'checkout') return <Checkout cart={cart} products={products} onBack={() => setPage('shop')} onComplete={complete} />
  if (page === 'operations') return <Operations products={products} onBack={() => setPage('shop')} onInventoryChange={refreshProducts} />
  if (page === 'success') return <Success order={order} onContinue={() => { setPage('shop'); setOrder(null); window.location.reload() }} />
  return (
    <div>
      <header className="site-header"><a className="brand" href="#top">REFIT<span>.</span></a><nav><a href="#shop">New in</a><a href="#story">Our story</a></nav><button className="studio-button" onClick={() => setPage('operations')}>Orders / seller studio</button><button className="bag-button" onClick={() => setDrawer(true)}><ShoppingBag /> Bag <span>{count}</span></button></header>
      <main id="top">
        <section className="hero"><div className="hero-copy"><span className="eyebrow">Pre-loved · reimagined</span><h1>Wear the story <em>forward.</em></h1><p>Considered pieces from real wardrobes, ready for their next chapter.</p><a className="primary-button" href="#shop">Explore the edit <ArrowRight /></a></div><div className="hero-art" aria-hidden="true"><div className="sun"></div><div className="coat-shape"><span>second</span><span>story</span></div><div className="orbit">20 ONE-OF-A-KIND FINDS · </div></div></section>
        <section className="value-strip"><p><Sparkles /> Curated condition</p><p>Independent sellers</p><p>Lower-impact wardrobes</p></section>
        <section className="catalog" id="shop"><div className="section-heading"><div><span className="eyebrow">The latest rotation</span><h2>Freshly refitted</h2></div><label className="search"><Search /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search the wardrobe" aria-label="Search products" /></label></div>
          <div className="filters" aria-label="Product categories">{categories.map(item => <button className={category === item ? 'active' : ''} key={item} onClick={() => setCategory(item)}>{item}</button>)}</div>
          {status === 'loading' && <div className="notice">Opening the wardrobe…</div>}
          {status === 'error' && <div className="notice error-message">The wardrobe is unavailable. Make sure the FastAPI backend is running on port 8000.</div>}
          {status === 'ready' && <div className="product-grid">{visible.map(product => <article className="product-card" key={product.id}><div className="art-wrap"><ProductArtwork product={product} />{product.featured && <span className="feature-tag">Editor's pick</span>}<button className="quick-add" onClick={() => add(product)} disabled={!product.stock}>{product.stock ? 'Quick add' : 'Sold out'} <Plus /></button></div><div className="product-info"><div><span>{product.category} · {product.condition}</span><h3>{product.name}</h3><p>Size {product.size} · sold by {product.seller}</p></div><strong>€{product.price.toFixed(2)}</strong></div></article>)}</div>}
          {status === 'ready' && visible.length === 0 && <div className="notice">No pieces match that edit.</div>}
        </section>
        <section className="story" id="story"><div><span className="eyebrow">One wardrobe at a time</span><h2>Nothing new.<br />Everything <em>renewed.</em></h2></div><div><p>Refit connects distinctive clothes with people who will actually wear them. Each listing is checked, clearly described, and kept in motion.</p><div className="story-stats"><span><strong>20</strong> launch pieces</span><span><strong>6</strong> categories</span><span><strong>1</strong> shared wardrobe</span></div></div></section>
      </main>
      <footer><a className="brand" href="#top">REFIT<span>.</span></a><p>Demo marketplace for quality assurance education.</p><p>© 2026 Refit</p></footer>
      {drawer && <CartDrawer cart={cart} products={products} onClose={() => setDrawer(false)} onQuantity={quantity} onCheckout={() => { setDrawer(false); setPage('checkout'); window.scrollTo(0, 0) }} />}
    </div>
  )
}

