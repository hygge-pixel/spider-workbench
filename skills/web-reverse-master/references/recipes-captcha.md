# Captcha Recipes

## Split The Problem

1. Initialization request.
2. Image or challenge solving.
3. Builder payload or track payload.
4. Environment or fingerprint dependency.
5. Final verify request and downstream token usage.

## Notes

- Treat captcha solving as protocol reconstruction, not browser automation delivery.
- Separate image solving from encrypted payload reconstruction.
- Record upstream token and cookie dependency explicitly in the plan.
