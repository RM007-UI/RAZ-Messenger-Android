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
- Chat translation uses Telegram's existing translation controller and API. A translucent iOS-inspired translation capsule is shown in chats with translatable messages; Premium access checks are preserved.
- Inter is used for Latin UI text; Noto Sans Arabic is the Arabic-script fallback on Android 10+ for Persian readability. Apple San Francisco is not bundled because Apple's font license does not grant general redistribution inside Android APKs; the fonts offered on third-party Iranian sites are modified builds with unclear app-embedding rights. Both fonts are bundled under the SIL Open Font License; their license texts are included in the APK assets and the source tree's third-party notices.
- A custom geometric dark launcher icon replaces Telegram's standard paper-plane branding.
- The first-run theme defaults to dark without overriding a theme the user has already selected.

The design takes inspiration from Apple's Liquid Glass guidance for navigation and controls, but RAZ uses Android-native rendering and its own assets. Apple's San Francisco font files are not bundled.

## Public GitHub prerelease

RAZ is configured to publish a **public GitHub prerelease** containing a signed, universal APK plus the customization source overlay. It must not fall back to Telegram's sample API credentials or the publicly known upstream test keystore.

Before the first public release, add these **GitHub Actions repository secrets** in **Settings → Secrets and variables → Actions**:

- `TG_API_ID` — the application ID created for RAZ at [my.telegram.org](https://my.telegram.org).
- `TG_API_HASH` — the matching application hash from the same application.
- `RAZ_RELEASE_KEYSTORE_BASE64` — a single-line Base64 encoding of RAZ's private release keystore.
- `RAZ_RELEASE_STORE_PASSWORD` — that keystore's store password.
- `RAZ_RELEASE_KEY_ALIAS` — the key alias inside the keystore.
- `RAZ_RELEASE_KEY_PASSWORD` — the private key password.

Create a new private release keystore and keep an offline backup safe. For example, run this locally with Java's `keytool` and choose strong, unique passwords when prompted:

```sh
keytool -genkeypair -v -keystore raz-release.jks -alias raz-release -keyalg RSA -keysize 3072 -validity 10000
```

Encode the keystore as a **single line** before pasting it into the `RAZ_RELEASE_KEYSTORE_BASE64` secret:

- Linux/Termux: `base64 -w0 raz-release.jks`
- macOS: `base64 -i raz-release.jks | tr -d '\\n'`
- PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("raz-release.jks"))`

Do not commit the keystore or any passwords/Base64 private-key content into the repository, and do not paste them into chat. Keep the original `.jks` file as an offline backup; **all future updates must use the exact same release key** or Android will reject the update over an already-installed release.

When all six secrets are present and valid, the workflow builds the non-debug `AfatRelease` variant, verifies its signature and both `armeabi-v7a`/32-bit and `arm64-v8a`/64-bit native libraries, then publishes a publicly downloadable GitHub prerelease. Each APK receives a unique version string and filename to avoid reinstalling an old build accidentally. GitHub Actions retains the run artifact for 90 days as a backup; the Release is the durable download location.

The current workflow deliberately **fails before building** when any required credential is missing. This prevents accidentally publishing a test APK using Telegram's public sample credentials or upstream's publicly available test signing key. Configure the secrets first, then run **Actions → Build RAZ public prerelease → Run workflow**, or push an intended release change to `main`.

RAZ is an independent Android client based on Telegram's GPL-2.0-or-later source, not an official Telegram product. A public binary release must be accompanied by the corresponding modified source and required third-party notices. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Translation and proxy compatibility

RAZ translation requirements and acceptance checks:

- **Translate a received message:** use Telegram's native message context-menu action (`TranslateAlert2`) and `messages.translateText`; the target is the selected received message, not text typed into a separate input field.
- **Translate entire chat:** use Telegram's native chat translation panel and automatic-translation controller. On fresh installs the per-message Translate action defaults to enabled; existing user preferences are preserved.
- **Show original:** retain Telegram's native original/translated message behavior.
- **Premium behavior:** keep Telegram's own entitlement checks and live-translation rules intact. Do not fake Premium status or bypass server-side access restrictions.
- **Privacy:** translation requests follow Telegram's documented translation path; users should be aware that translated message text may be processed by Telegram and its translation providers.

The proxy editor currently supports the upstream Telegram proxy types (SOCKS5, MTProto, and Telegram web proxy). VLESS, VMess, Trojan, Shadowsocks, and Hysteria are **not yet implemented as working tunnel protocols**. They must not be presented as connectable until a compatible, maintained engine is integrated and each URI format, connection lifecycle, and failure case is tested.

Visual acceptance is separate from translation behavior: compare the chat list, chat header, message bubbles, composer, menus, and bottom navigation against current Telegram iOS references; do not consider a palette-only change a completed iOS-style redesign.

## Performance principles

- Compile native libraries for 32-bit ARMv7 (`armeabi-v7a`) and 64-bit ARM64 (`arm64-v8a`) only; skip x86 ABIs to reduce build size.
- Keep the glass/blur effect on the navigation layer rather than adding broad blur across scrolling message content.
- Keep the official message/network implementation intact while improving theme, fonts, and branding.
- Avoid aggressive shrinking or obfuscation until a release build can be tested against login, messaging, media, calls, notifications, and background behavior.

## Licensing

Telegram's Android source is licensed under GPL-2.0-or-later. RAZ's customization files are intended to remain compatible with that license. See [the official source repository](https://github.com/DrKLO/Telegram) and `THIRD_PARTY_NOTICES.md`.
