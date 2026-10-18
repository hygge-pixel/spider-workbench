# Environment Patching Notes

- Patch only what the target code actually touches.
- Collect missing fields with proxies or controlled hooks first.
- Use CDP bridge only for temporary diagnosis/localization — final delivery must be a local offline implementation that does not depend on a running browser.
