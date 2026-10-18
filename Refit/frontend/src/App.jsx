import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Check, Minus, Plus, Search, ShoppingBag, Sparkles, X } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
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
  const subtotal = cart.reduce((sum, item) => sum + (products.find(p => p.id === item.productId)?.price || 0) * item.quantity, 0)
  const update = event => {
    const { name, value, type, checked } = event.target
    setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const response = await fetch(`${API_URL}/checkout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, country: form.country.toUpperCase(), coupon_code: form.coupon_code || null, card_number: form.card_number, items: cart.map(item => ({ product_id: item.productId, quantity: item.quantity })) }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Checkout could not be completed.')
      onComplete(data)
    } catch (reason) { setError(reason.message) } finally { setBusy(false) }
  }
  return (
    <main className="checkout-page">
      <button className="text-button" onClick={onBack}>← Back to shop</button>
      <div className="checkout-grid">
        <form className="checkout-form" onSubmit={submit}>
          <span className="eyebrow">Secure demonstration checkout</span><h1>Almost yours.</h1>
          <section><h2>Delivery details</h2><div className="form-grid">
            <label className="wide">Full name<input required name="customer_name" value={form.customer_name} onChange={update} autoComplete="name" /></label>
            <label className="wide">Email<input required type="email" name="email" value={form.email} onChange={update} autoComplete="email" /></label>
            <label className="wide">Address<input required name="address" value={form.address} onChange={update} autoComplete="street-address" /></label>
            <label>City<input required name="city" value={form.city} onChange={update} autoComplete="address-level2" /></label>
            <label>Postal code<input required name="postal_code" value={form.postal_code} onChange={update} autoComplete="postal-code" /></label>
            <label>Country code<input required name="country" value={form.country} onChange={update} maxLength="2" autoComplete="country" /></label>
          </div></section>
          <section><h2>Delivery method</h2><div className="shipping-options">
            {[['standard', 'Standard', '3–5 weekdays'], ['express', 'Express', '1–2 weekdays'], ['pickup', 'Pickup', 'From our studio']].map(([value, title, note]) => <label className={form.shipping_method === value ? 'selected' : ''} key={value}><input type="radio" name="shipping_method" value={value} checked={form.shipping_method === value} onChange={update} /><strong>{title}</strong><span>{note}</span></label>)}
          </div></section>
          <section><h2>Payment</h2><div className="form-grid">
            <label className="wide">Card number<input required name="card_number" value={form.card_number} onChange={update} inputMode="numeric" autoComplete="cc-number" /></label>
            <label>Expiry<input required name="expiry" value={form.expiry} onChange={update} placeholder="MM/YY" autoComplete="cc-exp" /></label>
            <label>CVV<input required name="cvv" value={form.cvv} onChange={update} inputMode="numeric" autoComplete="cc-csc" /></label>
            <label className="wide">Coupon (optional)<input name="coupon_code" value={form.coupon_code} onChange={update} placeholder="Try WELCOME10" /></label>
            <label className="check wide"><input type="checkbox" name="gift_wrap" checked={form.gift_wrap} onChange={update} /> Wrap this order as a gift</label>
          </div></section>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button className="primary-button full" disabled={busy}>{busy ? 'Placing your order…' : 'Buy now'} <ArrowRight /></button>
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

  useEffect(() => { fetch(`${API_URL}/products`).then(response => { if (!response.ok) throw new Error(); return response.json() }).then(data => { setProducts(data); setStatus('ready') }).catch(() => setStatus('error')) }, [])
  const visible = useMemo(() => products.filter(product => (category === 'all' || product.category === category) && (!query || `${product.name} ${product.description} ${product.seller}`.toLowerCase().includes(query.toLowerCase()))), [products, category, query])
  const count = cart.reduce((sum, item) => sum + item.quantity, 0)
  const add = product => { setCart(current => { const found = current.find(item => item.productId === product.id); return found ? current.map(item => item.productId === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) } : item) : [...current, { productId: product.id, quantity: 1 }] }); setDrawer(true) }
  const quantity = (productId, value) => setCart(current => value < 1 ? current.filter(item => item.productId !== productId) : current.map(item => item.productId === productId ? { ...item, quantity: value } : item))
  const complete = data => { setOrder(data); setCart([]); setPage('success'); window.scrollTo(0, 0) }
  if (page === 'checkout') return <Checkout cart={cart} products={products} onBack={() => setPage('shop')} onComplete={complete} />
  if (page === 'success') return <Success order={order} onContinue={() => { setPage('shop'); setOrder(null); window.location.reload() }} />
  return (
    <div>
      <header className="site-header"><a className="brand" href="#top">REFIT<span>.</span></a><nav><a href="#shop">New in</a><a href="#story">Our story</a></nav><button className="bag-button" onClick={() => setDrawer(true)}><ShoppingBag /> Bag <span>{count}</span></button></header>
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

