import { useEffect, useState } from 'react'
import { request } from './api'

function ReturnForm({ order, onReturn }) {
  const [productId, setProductId] = useState(order.lines[0].product.id)
  const [quantity, setQuantity] = useState(1)
  const [reason, setReason] = useState('fit')
  const [condition, setCondition] = useState('unworn')
  return <form className="operation-form" onSubmit={event => {
    event.preventDefault()
    onReturn({ product_id: Number(productId), quantity: Number(quantity), reason, condition, request_id: crypto.randomUUID() })
  }}>
    <h3>Request a return</h3>
    <label>Piece<select value={productId} onChange={e => setProductId(e.target.value)}>{order.lines.map(line => <option key={line.product.id} value={line.product.id}>{line.product.name} ({line.returned}/{line.quantity} returned)</option>)}</select></label>
    <label>Quantity<input type="number" min="1" max="10" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
    <label>Reason<select value={reason} onChange={e => setReason(e.target.value)}>{['fit', 'changed-mind', 'damaged', 'wrong-item'].map(value => <option key={value}>{value}</option>)}</select></label>
    <label>Condition<select value={condition} onChange={e => setCondition(e.target.value)}>{['unworn', 'opened', 'worn'].map(value => <option key={value}>{value}</option>)}</select></label>
    <button className="primary-button">Submit return</button>
  </form>
}

export default function Operations({ products, onBack, onInventoryChange }) {
  const [orderId, setOrderId] = useState(localStorage.getItem('refit-order') || '')
  const [order, setOrder] = useState(null)
  const [orders, setOrders] = useState([])
  const [loadingOrders, setLoadingOrders] = useState(true)
  const [orderListError, setOrderListError] = useState('')
  const [seller, setSeller] = useState(products[0]?.seller || '')
  const [summary, setSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [summaryRefresh, setSummaryRefresh] = useState(0)
  const [listing, setListing] = useState(products[0]?.id || '')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    request('/orders').then(async rows => {
      if (!active) return
      setOrders(rows)
      const selected = rows.some(row => row.order_id === orderId) ? orderId : rows[0]?.order_id || ''
      setOrderId(selected)
      if (selected) {
        const savedOrder = await request(`/orders/${encodeURIComponent(selected)}`)
        if (!active) return
        setOrder(savedOrder)
        setSeller(savedOrder.lines[0].product.seller)
      }
    }).catch(error => { if (active) setOrderListError(error.message) })
      .finally(() => { if (active) setLoadingOrders(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!seller && products.length) setSeller(products[0].seller)
  }, [products, seller])

  useEffect(() => {
    if (!seller) return
    let active = true
    setLoadingSummary(true)
    setSummary(null)
    setSummaryError('')
    request(`/sellers/${encodeURIComponent(seller)}/summary`).then(result => {
      if (active) setSummary(result)
    }).catch(error => { if (active) setSummaryError(error.message) })
      .finally(() => { if (active) setLoadingSummary(false) })
    return () => { active = false }
  }, [seller, order, summaryRefresh])

  async function run(action) {
    setBusy(true)
    setFeedback('')
    try { await action() } catch (error) { setFeedback(error.message) } finally { setBusy(false) }
  }
  async function reloadOrder() {
    const updated = await request(`/orders/${encodeURIComponent(orderId)}`)
    setOrder(updated)
    setSeller(updated.lines[0].product.seller)
    setOrders(current => current.map(row => row.order_id === updated.order_id ? { ...row, status: updated.status } : row))
  }
  function changeOrder(path, method = 'POST', body) {
    run(async () => {
      const result = await request(`/orders/${order.order_id}/${path}`, { method, body })
      setFeedback(result.refund === undefined ? 'Order updated.' : `Return approved. Refund: €${result.refund.toFixed(2)}`)
      await reloadOrder()
      onInventoryChange()
    })
  }
  return <main className="checkout-page operations">
    <button className="text-button" onClick={onBack}>← Back to shop</button>
    <h1>Orders and seller studio</h1>
    <p>Choose a saved order to follow your purchase. Seller and fulfilment controls use demonstration data.</p>
    <fieldset disabled={busy}>
      <section className="operation-card">
        <form className="operation-form" onSubmit={e => { e.preventDefault(); run(reloadOrder) }}>
          <label>Order reference<select required disabled={loadingOrders || !orders.length} value={orderId} onChange={e => { setOrderId(e.target.value); setOrder(null); setFeedback(''); localStorage.setItem('refit-order', e.target.value) }}>
            {!orders.length && <option value="">{loadingOrders ? 'Loading orders…' : 'No orders yet'}</option>}
            {orders.map(row => <option key={row.order_id} value={row.order_id}>{row.order_id} · {new Date(row.created_at).toLocaleString()} · €{row.total.toFixed(2)} · {row.status}</option>)}
          </select></label>
          <button className="primary-button" disabled={loadingOrders || !orderId}>Find order</button>
        </form>
        {orderListError && <p className="error-message" role="alert">Could not load orders: {orderListError}</p>}
        {!loadingOrders && !orderListError && !orders.length && <p>Your purchases will appear here after checkout.</p>}
        {order && <>
          <h2>{order.order_id} · {order.status}</h2>
          <p>Paid €{order.totals.total.toFixed(2)} · refunded €{order.refunded.toFixed(2)}</p>
          <ul>{order.lines.map(line => <li key={line.product.id}>{line.quantity} × {line.product.name} · sold by {line.product.seller}</li>)}</ul>
          <div className="operation-actions">
            <button onClick={() => changeOrder('cancel')} disabled={order.status !== 'placed'}>Cancel order</button>
            <button onClick={() => changeOrder('status', 'PATCH', { status: 'dispatched' })} disabled={order.status !== 'placed'}>Mark dispatched</button>
            <button onClick={() => changeOrder('status', 'PATCH', { status: 'delivered' })} disabled={order.status !== 'dispatched'}>Mark delivered</button>
          </div>
          {['delivered', 'partially-returned'].includes(order.status) && <ReturnForm key={order.order_id} order={order} onReturn={body => changeOrder('returns', 'POST', body)} />}
        </>}
      </section>
      <section className="operation-card">
        <h2>Seller summary</h2>
        <p>New purchases appear below immediately. Earnings remain pending until the order is marked delivered.</p>
        <form className="operation-form" onSubmit={e => { e.preventDefault(); setSummaryRefresh(value => value + 1) }}>
          <label>Seller<select aria-label="Seller" value={seller} onChange={e => setSeller(e.target.value)}>{[...new Set(products.map(p => p.seller))].sort().map(name => <option key={name}>{name}</option>)}</select></label>
          <button className="primary-button" disabled={!seller || loadingSummary}>Refresh seller summary</button>
        </form>
        {loadingSummary && <p aria-live="polite">Loading seller summary…</p>}
        {summaryError && <p className="error-message" role="alert">Could not load seller summary: {summaryError}</p>}
        {summary && <div className="seller-summary" aria-live="polite">
          <h3>{summary.seller} · {summary.tier}</h3>
          <dl className="seller-totals">
            <div><dt>Sales after refunds</dt><dd>€{summary.total_sales.toFixed(2)}</dd></div>
            <div><dt>Estimated earnings after commission</dt><dd>€{summary.estimated_earnings.toFixed(2)}</dd></div>
            <div><dt>Pending earnings</dt><dd>€{summary.pending_payout.toFixed(2)}</dd></div>
            <div><dt>Available payout estimate</dt><dd>€{summary.payout.toFixed(2)}</dd></div>
          </dl>
          <p>Awaiting delivery: sales €{summary.pending_sales.toFixed(2)} · commission €{summary.pending_commission.toFixed(2)}.</p>
          <p>Delivered: sales €{summary.gross.toFixed(2)} · commission €{summary.commission.toFixed(2)}.</p>
          {summary.pending_sales > 0 && <p>To move pending earnings to the available estimate, find the order above, then mark it dispatched and delivered.</p>}
          {summary.total_sales === 0 && <p>This seller has no remaining sales after cancellations and refunds.</p>}
          <p>Sales include allocated tax and exclude delivery and gift wrapping. Estimates are not actual bank transfers.</p>
        </div>}
      </section>
      <section className="operation-card">
        <h2>Listing review</h2>
        <label>Listing<select aria-label="Listing" value={listing} onChange={e => setListing(e.target.value)}>{products.map(product => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
        <div className="operation-actions">{['review', 'approve', 'reject'].map(action => <button key={action} onClick={() => run(async () => {
          const result = await request(`/products/${listing}/moderation`, { method: 'POST', body: { action } })
          setFeedback(`${result.status}: ${result.reasons.join('; ') || 'Listing review complete'}`)
          onInventoryChange()
        })}>{action}</button>)}</div>
      </section>
    </fieldset>
    {feedback && <p className="operation-feedback" role="status">{feedback}</p>}
  </main>
}
