# Signature Recipes

## Common Patterns

- `MD5/SHA`: verify exact input string order before hashing.
- `HMAC`: confirm key source, string encoding, and output format.
- `AES`: confirm mode, IV, padding, and whether the key is raw text, hex, or derived.
- `RSA`: confirm PEM/public key source and padding mode.
- `WASM`: prefer local execution or browser-side bridge over blind rewrites.
- `TLS fingerprint`: use a browser or `curl_cffi` only after algorithm parity is already confirmed.

## Parity Checklist

1. Compare raw input context.
2. Compare intermediate string.
3. Compare encoded bytes.
4. Compare final output.
