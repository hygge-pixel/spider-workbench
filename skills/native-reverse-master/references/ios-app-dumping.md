# iOS App Dumping

Load this reference only for an authorized application and device when an encrypted App Store image prevents the requested static analysis.

## Authorization and scope

Record bundle identifier, exact process, app/build version, device ownership/authorization, permitted extraction scope, and handling rules. Do not assume permission to jailbreak, alter code signing, bypass device policy, or collect unrelated keychain/account data.

## Evidence contract

Inventory the bundle, Mach-O slices, encryption/load commands, frameworks, extensions, resources, and signatures. If an authorized runtime extraction is used, preserve the original and recovered hashes, architecture slice, load address, command/tool version, and validation result.

Validate that the recovered slice parses, has the expected architecture/build identity, and addresses the named analysis gap. Keep partial segments `partial`; a loadable header alone is not a complete executable.

Static Mach-O symbols/structures remain in this skill. Objective-C/Swift call-flow questions use symbol/structure references; request/network logic can hand off to `web-reverse-workflow` with redacted samples.
