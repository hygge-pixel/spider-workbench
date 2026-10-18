# IDA Python Automation

Load this reference when a repeatable IDA database query or narrowly scoped annotation is more reliable than manual clicking.

## Script contract

- pin the expected IDA/Python API version and database/input hash;
- separate read-only queries from database mutations;
- accept addresses/names as explicit inputs, not hidden globals;
- emit JSON/CSV or deterministic comments with address, evidence, and failures;
- make annotation writes idempotent and preserve analyst-authored names/comments;
- bound function, segment, xref, and decompilation iteration counts.

Use read-only scripts first for functions, strings, xrefs, callers/callees, imports, segments, instruction operands, and pseudocode availability. Request permission before mass renaming, type application, patching, or database export.

Validate outputs against at least one known address and the current image base. Treat failed decompilation as an explicit result, not an empty function. Keep Hex-Rays-only logic optional and detect availability before use.
