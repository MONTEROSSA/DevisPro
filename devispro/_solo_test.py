import os, sys
sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto')
sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')
from devispro.billing import create_checkout_session
env = open(os.path.expanduser('~/.devispro_stripe.env')).read()
key_line = [l for l in env.split('\n') if l.startswith('STRIPE_API_KEY=')][0]
token = key_line.split('"')[1]
os.environ['STRIPE_API_KEY'] = token
try:
    result = create_checkout_session('solo', 'test@devispro.ch', 'https://devispro.de/success', 'https://devispro.de/cancel')
    if 'checkout_url' in result:
        print(f"SUCCESS: {result['checkout_url'][:80]}...")
        print(f"SESSION: {result['session_id']}")
    else:
        print(f"ERROR: {result.get('error', '?')}")
except Exception as e:
    print(f"EXCEPTION: {e}")