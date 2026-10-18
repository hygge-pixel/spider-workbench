# Tooling and Diagnostics

Read this reference when choosing a decompiler or diagnosing missing local tools. Tools are optional external dependencies; their presence is not proof that a target is analyzable.

## Read-only dependency report

```powershell
py -3.11 skills/android-reverse-engineering/scripts/check_dependencies.py --json
```

The command checks executables only. It will not download packages, invoke a package manager, mutate PATH, or start a device/browser.

## Decompiler choice

| Situation | Preferred action |
|---|---|
| First APK pass with resources | jadx |
| JAR or ordinary Java library | Vineflower, optionally compare with jadx |
| jadx reports broken methods | compare only affected classes with Vineflower after an explicit DEX-to-JAR step |
| Large package, code-only question | jadx without resource decoding |
| Flutter/Unity/Xamarin/React Native owner | switch to the framework artifact; do not spend the first pass on Java wrappers |

Use an explicit output directory inside the task evidence area. Record the command, version, input SHA-256, exit status, warnings, and output hash/inventory. Bound memory, threads, and method timeouts for large or adversarial inputs.

## Safe jadx examples

```powershell
jadx --no-res --show-bad-code -d <output> <artifact.apk>
jadx --deobf --show-bad-code -d <output> <artifact.apk>
```

Use `jadx-gui` only when interactive navigation materially helps. Do not claim that GUI availability validates a skill or package.

## Vineflower boundary

Vineflower reads Java bytecode, not Android DEX directly. APK/DEX analysis therefore needs an explicitly installed conversion tool and a separately recorded intermediate hash. Compare outputs class-by-class; do not mix decompiler output without provenance.

## ADB/device boundary

ADB, package installation, process attach, filesystem pulls, and runtime instrumentation affect an external device. Require an explicitly authorized device and exact package/process before those actions. Static package inspection does not authorize runtime work.
