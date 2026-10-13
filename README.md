# RAZ (راز) — Android client based on Telegram

**Project status: starter scaffold. No APK has been built yet.**

RAZ is an independent Android client built by customizing the official [Telegram for Android](https://github.com/DrKLO/Telegram) source at build time. This repository contains our branding overlay and build workflow; the large upstream source is fetched by GitHub Actions.

- App name: **RAZ / راز**
- Android application ID: `com.rm007.raz` (debug app ID: `com.rm007.raz.beta`)
- Intended initial device: Redmi Note 9 Pro (ARM64)
- Build workflow: `.github/workflows/build-android.yml`

## First-time setup

1. Get your own Telegram API ID and API hash from [my.telegram.org](https://my.telegram.org).
2. In this repository, open **Settings → Secrets and variables → Actions** and add:
   - `TG_API_ID`: your numeric API ID
   - `TG_API_HASH`: your API hash (32 hexadecimal characters)
3. Open **Actions → Build RAZ Android APK → Run workflow**.
4. On success, download the `RAZ-debug-arm64` artifact. The archive includes `RAZ-debug-arm64.apk` and the upstream commit record.

Keep API credentials in GitHub Actions secrets; never commit them to this repository.

## What the current build does

- Applies RAZ's launcher icon, display name and Android package ID.
- Configures the app with the developer API credentials supplied through secrets.
- Limits native compilation to ARM64 to reduce unnecessary build work.
- Produces an unsigned-for-release / debug-signed test APK from the official Telegram Android Gradle task.

The workflow fetches the current upstream default branch, so builds may change over time. The exact upstream commit is saved in the artifact as `upstream-commit.txt`.

## Known limitations

- **No real GitHub Actions build has been run yet**, and the APK has not been installed or tested on a phone.
- Push notifications and other Google services still require RAZ's own Firebase / service configuration. Changing the package ID alone does not configure working push notifications.
- The APK is a test build, not a public release. Before distributing it, establish a release signing key, stable versioning, service configuration and a privacy policy.
- RAZ is an unofficial, independent client and must not be represented as an official Telegram product.

## License

The upstream Telegram for Android source is licensed under GPL-2.0-or-later. RAZ customization files are also provided under GPL-2.0-or-later. When distributing a modified client, comply with the upstream license and provide the corresponding source and required notices. See the upstream project: https://github.com/DrKLO/Telegram
