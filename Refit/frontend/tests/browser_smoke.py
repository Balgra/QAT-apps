"""Run against a freshly started Refit backend. Requires Playwright and Chrome."""
import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright


def validate_delivery_feedback(page, base_url):
    page.goto(base_url)
    page.locator('article.product-card').filter(has_text='Cloud Knit Sweater').get_by_role('button', name='Quick add').click()
    page.get_by_role('button', name='Proceed to checkout').click()
    checkout_requests = []
    page.on('request', lambda request: checkout_requests.append(request) if request.method == 'POST' and request.url.endswith('/api/checkout') else None)
    for label in ['Full name', 'Email', 'Address', 'City', 'Postal code', 'Country code', 'Card number', 'Expiry', 'CVV']:
        page.get_by_label(label, exact=True).fill('a')
    location = page.url
    page.get_by_role('button', name='Buy now').click()
    expect(page.get_by_role('alert')).to_contain_text('Please correct the highlighted fields')
    for label in ['Full name', 'Email', 'Address', 'City', 'Postal code', 'Country code', 'Card number', 'Expiry', 'CVV']:
        field = page.get_by_label(label, exact=True)
        expect(field).to_have_attribute('aria-invalid', 'true')
        expect(field).to_have_value('a')
        described_by = field.get_attribute('aria-describedby')
        expect(page.locator(f'#{described_by}')).to_be_visible()
    expect(page.get_by_label('Full name', exact=True)).to_be_focused()
    assert page.url == location and not checkout_requests

    for label, value in [('Full name', 'Åsa O’Neill'), ('Email', 'asa@example.com'), ('Address', 'Example Street 12'),
                         ('City', 'Göteborg'), ('Postal code', '41257'), ('Country code', 'SE'),
                         ('Card number', '4242 4242 4242 4242'), ('Expiry', '12/35'), ('CVV', '123')]:
        page.get_by_label(label, exact=True).fill(value)
    page.route('**/api/checkout', lambda route: route.fulfill(status=422, content_type='application/json', body=json.dumps({
        'detail': [{'loc': ['body', 'postal_code'], 'msg': 'Value error, Postal code is unavailable for this address.'}]
    })))
    page.get_by_role('button', name='Buy now').click()
    expect(page.get_by_label('Postal code', exact=True)).to_be_focused()
    expect(page.locator('#checkout-postal_code-error')).to_have_text('Postal code is unavailable for this address.')
    expect(page.get_by_label('Address', exact=True)).to_have_value('Example Street 12')
    page.unroute('**/api/checkout')
    page.route('**/api/checkout', lambda route: route.fulfill(status=400, content_type='application/json', body=json.dumps({
        'detail': 'The demonstration card number is invalid'
    })))
    page.get_by_role('button', name='Buy now').click()
    expect(page.get_by_role('alert')).to_have_text('The demonstration card number is invalid')
    expect(page.get_by_role('alert')).to_be_focused()
    expect(page.get_by_role('heading', name='Almost yours.')).to_be_visible()
    assert page.url == location
    page.unroute('**/api/checkout')
    print('Delivery validation passed: invalid form blocked; inline/API errors visible; entered values retained')


def run(base_url):
    with sync_playwright() as engine:
        browser = engine.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base_url)
        page.get_by_role('button', name='Orders / seller studio').click()
        expect(page.get_by_label('Order reference')).to_be_disabled()
        expect(page.get_by_text('Your purchases will appear here after checkout.')).to_be_visible()
        expect(page.get_by_role('button', name='Find order')).to_be_disabled()
        expect(page.get_by_label('Seller', exact=True).locator('option')).to_have_text(['Ava', 'Elias', 'Linnea', 'Mira', 'Noah'])
        validate_delivery_feedback(page, base_url)
        previous = page.request.post(f'{base_url}/api/checkout', data={
            'items': [{'product_id': 3, 'quantity': 1}], 'customer_name': 'Earlier Shopper',
            'email': 'earlier@example.com', 'address': 'Example Street 12', 'city': 'Gothenburg',
            'postal_code': '41257', 'country': 'SE', 'card_number': '4242424242424242', 'expiry': '12/35', 'cvv': '123',
        })
        assert previous.status == 200, previous.text()
        previous_id = previous.json()['order_id']
        page.goto(base_url)
        card = page.locator("article.product-card").filter(has_text="Cloud Knit Sweater")
        card.get_by_role("button", name="Quick add").click()
        page.get_by_role("button", name="Proceed to checkout").click()
        for label, value in [("Full name", "Browser Shopper"), ("Email", "browser@example.com"),
                             ("Address", "Example Street 12"), ("City", "Gothenburg"), ("Postal code", "41257")]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role("button", name="Review final total").click()
        expect(page.get_by_role("heading", name=re.compile(r"Total €"))).to_be_visible()
        page.get_by_role("button", name="Hold these pieces for 10 minutes").click()
        expect(page.get_by_role("button", name="Release hold")).to_be_visible()
        page.get_by_role("button", name="Buy now").click()
        expect(page.get_by_role("heading", name="Thank you.")).to_be_visible()
        page.get_by_role("button", name="Continue browsing").click()
        page.get_by_role("button", name="Orders / seller studio").click()
        references = page.get_by_label('Order reference')
        expect(references.locator('option')).to_have_count(2)
        latest_id = references.input_value()
        assert latest_id != previous_id
        expect(page.get_by_label('Seller', exact=True)).to_have_value('Linnea')
        expect(page.get_by_role('heading', name='Linnea · standard')).to_be_visible()
        expect(page.locator('.seller-totals div').filter(has_text='Sales after refunds').locator('dd')).to_have_text('€52.50')
        expect(page.locator('.seller-totals div').filter(has_text='Pending earnings').locator('dd')).to_have_text('€47.25')
        expect(page.locator('.seller-totals div').filter(has_text='Available payout estimate').locator('dd')).to_have_text('€0.00')
        references.select_option(previous_id)
        page.get_by_role('button', name='Find order').click()
        expect(page.get_by_role('heading', name=f'{previous_id} · placed')).to_be_visible()
        expect(page.get_by_role('heading', name='Noah · standard')).to_be_visible()
        references.select_option(latest_id)
        page.get_by_role("button", name="Find order").click()
        expect(page.get_by_role("heading", name=re.compile(r"RF-.*placed"))).to_be_visible()
        page.get_by_role("button", name="Mark dispatched").click()
        expect(page.get_by_role("button", name="Mark delivered")).to_be_enabled()
        page.get_by_role("button", name="Mark delivered").click()
        expect(page.locator('.seller-totals div').filter(has_text='Available payout estimate').locator('dd')).to_have_text('€47.25')
        expect(page.locator('.seller-totals div').filter(has_text='Pending earnings').locator('dd')).to_have_text('€0.00')
        page.get_by_role("button", name="Submit return").click()
        expect(page.get_by_role("status")).to_contain_text("Return approved")
        expect(references.locator('option:checked')).to_contain_text('returned')
        page.get_by_label("Seller", exact=True).select_option("Linnea")
        expect(page.locator('.seller-totals div').filter(has_text='Available payout estimate').locator('dd')).to_have_text('€0.00')
        expect(page.locator('.seller-totals div').filter(has_text='Sales after refunds').locator('dd')).to_have_text('€0.00')
        page.get_by_label('Seller', exact=True).select_option('Noah')
        expect(page.locator('.seller-totals div').filter(has_text='Pending earnings').locator('dd')).to_have_text('€61.87')
        page.get_by_label('Seller', exact=True).select_option('Linnea')
        page.get_by_role('button', name='Refresh seller summary').click()
        expect(page.get_by_role('heading', name='Linnea · standard')).to_be_visible()
        page.get_by_label("Listing", exact=True).select_option("2")
        page.get_by_role("button", name="review", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("approved")
        page.get_by_role("button", name="Back to shop", exact=False).click()
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("button", name="Orders / seller studio")).to_be_visible()
        page.get_by_role('button', name='Orders / seller studio').click()
        expect(page.get_by_label('Order reference')).to_have_value(latest_id)
        expect(page.get_by_label('Order reference').locator('option')).to_have_count(2)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile horizontal overflow"
        with page.expect_download() as downloading:
            page.evaluate("""() => {
                const link = document.createElement('a')
                link.href = '/api/activity-log'
                document.body.appendChild(link)
                link.click()
                link.remove()
            }""")
        download = downloading.value
        assert download.suggested_filename == 'refit-activity-log.json'
        document = json.loads(Path(download.path()).read_text(encoding='utf-8'))
        purchases = [row for row in document['events'] if row['path'] == '/api/checkout']
        assert len(purchases) == 2
        assert all(row['request']['payload']['value']['card_number'] == '[REDACTED]' for row in purchases)
        assert all(row['response']['status_code'] == 200 for row in purchases)
        assert all(row['response']['payload']['value']['order_id'] for row in purchases)
        assert all(row['path'] != '/api/activity-log' for row in document['events'])
        assert not errors, errors
        browser.close()
        print("Browser smoke passed: quote, reservation, checkout, fulfilment, return, seller, moderation, mobile viewport")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    run(parser.parse_args().base_url)
