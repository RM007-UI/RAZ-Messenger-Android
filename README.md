# RAZ (راز) — Android messaging client

**Status:** The initial ARM64 APK was verified on a Redmi Note 9 Pro, including account sign-in and message sending/receiving. The refreshed iOS-inspired dark UI is now being built as a dual-ABI APK for 32-bit ARMv7 and 64-bit ARM64.

RAZ is an independent Android client based on the official [Telegram for Android source](https://github.com/DrKLO/Telegram). It is not an official Telegram product.

- App name: **RAZ / راز**
- Android application ID: `com.rm007.raz` (debug application ID: `com.rm007.raz.beta`)
- Tested device: Redmi Note 9 Pro (ARM64); 32-bit ABI is configured but still needs a physical 32-bit-device test
- Upstream source is pinned in `.github/workflows/build-android.yml`

## Visual direction

- Deep graphite/black surfaces, cool silver highlights, and an iOS-inspired blue accent.
- The pinned Telegram source already contains a blur-backed glass navigation bar. RAZ tunes the glass tab palette instead of applying expensive blur to the entire message content.
- Inter is used for the Latin interface; Noto Sans Arabic is the preferred Arabic-script fallback on Android 10+ for Persian readability. Both fonts are bundled under the SIL Open Font License; their license texts are included in the APK assets and the source tree's third-party notices.
- A custom geometric dark launcher icon replaces Telegram's standard paper-plane branding.
- The first-run theme defaults to dark without overriding a theme the user has already selected.

The design takes inspiration from Apple's Liquid Glass guidance for navigation and controls, but RAZ uses Android-native rendering and its own assets. Apple's San Francisco font files are not bundled.

## Build a test APK

1. Open the repository's **Actions** tab.
2. Select **Build RAZ Android APK**.
3. Press **Run workflow**.
4. When the run succeeds, download the `RAZ-debug-armv7-arm64` artifact. It is configured to contain both `armeabi-v7a` (32-bit ARM) and `arm64-v8a` (64-bit ARM).

The normal workflow downloads the pinned Telegram Android source, applies RAZ branding, configures both `armeabi-v7a` and `arm64-v8a`, and creates a debug-signed multi-ABI test APK. Each build pins the same upstream source and uses the same upstream test keystore, so update signatures are consistent across test builds.

## Telegram API credentials and public distribution

The initial test build used the sample API credentials in the pinned upstream source; sign-in and messaging worked in the user's device test. That does not make sample credentials appropriate for distributing an app. Before a public release:

1. Obtain and use RAZ's own `TG_API_ID` and `TG_API_HASH` from [my.telegram.org](https://my.telegram.org).
2. Keep credentials in GitHub Actions secrets, never in source control.
3. Configure RAZ's own Firebase services if push notifications are required.
4. Set up a stable release-signing key, release versioning, privacy policy, and a tested update process.
5. Follow Telegram's branding requirements and comply with the upstream GPL-2.0-or-later license, including providing the corresponding modified source and required notices.

The workflow still permits a test-only build with upstream sample credentials when both secrets are absent. Do not distribute that test build publicly.

## Signing consistency and public release

The pinned upstream Telegram Android source explicitly configures the debug APK to use `TMessagesProj/config/release.keystore` with alias `androidkey`. Because each RAZ build downloads the same pinned upstream commit, that signing identity remains the same between these test builds, so a new test APK should update the currently installed RAZ without a signature-mismatch uninstall.

Important security distinction: this is a keystore shipped in the public upstream source, not a private RAZ release key. It is suitable only for internal/test builds and must not be used for a public distribution. A real public release needs a newly generated RAZ-owned release keystore kept out of source control and supplied to GitHub Actions through secrets.

The APK artifact contains `RAZ-source-overlay.zip` with the important project customization files and `RAZ-signing-certificate-sha256.txt` so the signing identity can be compared across builds. A separate `RAZ-upstream-test-signing-key-reference` artifact backs up the actual test keystore used for reproducible test builds.

## Performance principles

- Compile native libraries for 32-bit ARMv7 (`armeabi-v7a`) and 64-bit ARM64 (`arm64-v8a`) only; skip x86 ABIs to reduce build size.
- Keep the glass/blur effect on the navigation layer rather than adding broad blur across scrolling message content.
- Keep the official message/network implementation intact while improving theme, fonts, and branding.
- Avoid aggressive shrinking or obfuscation until a release build can be tested against login, messaging, media, calls, notifications, and background behavior.

## Licensing

Telegram's Android source is licensed under GPL-2.0-or-later. RAZ's customization files are intended to remain compatible with that license. See [the official source repository](https://github.com/DrKLO/Telegram) and `THIRD_PARTY_NOTICES.md`.
