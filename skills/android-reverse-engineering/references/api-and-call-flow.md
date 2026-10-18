# API and Call-Flow Analysis

Read this reference when producing endpoint inventories or tracing a UI/background event to a network request.

## Start from durable anchors

R8 can rename classes and methods, but literals, manifests, annotations, public library APIs, serialization names, and many metadata strings remain useful. Search first for:

- Retrofit method annotations and parameter annotations;
- Ktor `HttpClient`, request verbs, `defaultRequest`, `BearerTokens`, and refresh callbacks;
- OkHttp request builders, interceptors, authenticators, and `HttpUrl` construction;
- Volley request subclasses and queues;
- Apollo client server URLs and generated operations;
- `WebView.loadUrl`, `addJavascriptInterface`, fetch/XHR bridge calls;
- URL/path literals, host constants, content types, auth header names, error messages, and DTO field names.

## Flat inventory first

Always build a deduplicated Tier 1 table before tracing individual endpoints:

| Host/base | Method | Path/operation | Auth evidence | Request type | Response type | Source |
|---|---|---|---|---|---|---|

Use `?` for unknown values. Never infer an HTTP method solely from a path name. Preserve file and line references so another analyst can reproduce each row.

Create Tier 2 detail only for user-selected flows, authentication/session refresh, payments/orders, custom signing, or anomalous headers. Include the call chain, parameter sources, state dependencies, interceptors, retry behavior, and positive sample availability.

## Trace the call chain

Use the narrowest observable chain that reaches the request:

```text
manifest/deep link/UI event/background trigger
  -> Activity/Fragment/Compose callback/Worker/Service
  -> ViewModel/Presenter/UseCase
  -> Repository/data source
  -> DI binding or factory
  -> HTTP interface/client/interceptor
  -> serialized request
```

For Dagger/Hilt, map `@Module`, `@Provides`, `@Binds`, components, and injected constructors. For Koin, find module declarations, `single`/`factory`/`viewModel` bindings, and resolution sites. For obfuscated lambdas, anchor on constructed types and captured fields rather than generated class names.

## Authentication and signing

Separate four evidence layers:

1. Token origin: login, bootstrap, storage, device binding, or refresh.
2. Token placement: header, cookie, query, body, or WebView bridge.
3. Transform: serialization, canonicalization, hash/MAC/encryption, encoding.
4. Transport/session state: redirects, cookies, TLS/HTTP profile, challenge state.

If the algorithm is known and positive input/output samples exist, hand off to `web-reverse-test-driven-development` or `param-encryptor`. If the logic belongs to native code, hand off to `native-reverse-master`. Do not claim parity from static source resemblance alone.

## Deliverable

Provide the Tier 1 table, a bounded set of Tier 2 traces, evidence locations, confidence/status per claim, and unresolved edges. Redact secret values while preserving field names and provenance.
