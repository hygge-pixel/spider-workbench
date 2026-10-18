# Package Workflow

Read this reference for initial APK, XAPK, JAR, or AAR triage.

## 1. Preserve the artifact

Record the absolute source path, SHA-256, size, acquisition provenance, and authorization scope. Work from a copy when later tools can modify their inputs. Session files and secrets remain task-local and uncommitted.

## 2. Inventory without extraction

Run:

```powershell
py -3.11 skills/android-reverse-engineering/scripts/inspect_package.py <artifact> --json
```

The inspector reads the ZIP central directory, enforces member/count limits, and reports manifests, DEX files, native libraries, resource archives, and framework markers. It never extracts or executes entries.

For XAPK, inventory nested APK names before selecting the base package. Split configuration packages often own ABI libraries while the base package owns managed code and resources.

## 3. Select the target family

| Evidence | Next analysis |
|---|---|
| `classes*.dex`, Android manifest, Retrofit/Ktor/OkHttp | jadx-managed Android workflow |
| `libflutter.so`, `libapp.so`, `flutter_assets/` | Flutter asset/Dart and native workflow; do not expect jadx to recover app logic |
| `index.android.bundle`, React Native libraries | JavaScript bundle plus native bridge inventory |
| `assets/www/`, Capacitor/Cordova configuration | Web assets and WebView bridge; route browser protocol work to `web-reverse-workflow` |
| Xamarin assemblies or Mono libraries | Managed assembly workflow plus native bridge inventory |
| `libunity.so`, `libil2cpp.so`, `global-metadata.dat` | `native-reverse-master`, Unity IL2CPP reference |
| Unknown framework | Keep the result `unknown`; use strings, dependencies, and entry points before choosing tools |

Hybrid markers can be real. Report all observed markers and identify which component owns the requested behavior.

## 4. Native Android structure

After decompilation, inspect in this order:

1. `AndroidManifest.xml`: application class, launcher activities, exported components, services, receivers, providers, permissions, deep links.
2. Every module `BuildConfig`: hosts, flavors, feature flags, and non-secret configuration.
3. Package boundaries: first-party code versus SDKs and generated code.
4. HTTP and serialization stack: Retrofit, OkHttp, Ktor, Volley, Apollo, Gson, Moshi, Jackson, kotlinx serialization.
5. DI stack: Hilt/Dagger, Koin, manual factories/service locators.
6. Native bridges: JNI method declarations, `System.loadLibrary`, WebView JavaScript interfaces, and platform channels.

Do not treat a hardcoded key or URL as live. Redact credentials in reports and state only its type, location, and evidence hash.

## Stop conditions

Stop this phase when the framework and owning component are known, the relevant package/split is identified, and the next step has a specific artifact and question. Do not broaden from one authorized package to related accounts, services, or devices.
