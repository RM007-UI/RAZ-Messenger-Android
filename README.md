# RAZ (راز) — Android client based on Telegram

**Project status: starter scaffold. No APK has been built yet.**

RAZ is an independent Android client built by customizing the official [Telegram for Android](https://github.com/DrKLO/Telegram) source at build time. This repository contains our branding overlay and build workflow; the large upstream source is fetched by GitHub Actions.

- App name: **RAZ / راز**
- Android application ID: `com.rm007.raz` (debug app ID: `com.rm007.raz.beta`)
- Intended initial device: Redmi Note 9 Pro (ARM64)
- Build workflow: `.github/workflows/build-android.yml`

## Build a test APK now

You can try the build before Telegram approves your own API credentials:

1. Open the repository's **Actions** tab.
2. Select **Build RAZ Android APK**.
3. Press **Run workflow** and confirm **Run workflow**.
4. When the run succeeds, open it and download the `RAZ-debug-arm64` artifact. It contains `RAZ-debug-arm64.apk` and the upstream commit record.

If `TG_API_ID` and `TG_API_HASH` are both absent, the workflow preserves the sample API credentials supplied in the pinned upstream source. Telegram documents those credentials as suitable for testing only. This test build may install and launch, but **login and real Telegram connectivity are not guaranteed**. Do not distribute it or use those sample credentials for a public app.

## Configure your own Telegram API credentials

For a functional client, obtain your own API credentials from [my.telegram.org](https://my.telegram.org). If the site keeps showing only `ERROR`, the build-only test path above can proceed while the registration issue is investigated.

In this repository, open **Settings → Secrets and variables → Actions** and add:

- `TG_API_ID`: your numeric API ID
- `TG_API_HASH`: your API hash (32 hexadecimal characters)

Keep API credentials in GitHub Actions secrets; never commit them to this repository. Once both secrets exist, the workflow automatically uses them instead of the upstream test credentials.

## What the current build does

- Applies RAZ's launcher icon, display name and Android package ID.
- Uses your API credentials if supplied, otherwise keeps the pinned upstream sample credentials for test builds only.
- Limits native compilation to ARM64 to reduce unnecessary build work.
- Produces a debug-signed test APK from the official Telegram Android Gradle task.

The workflow pins the official Telegram source to commit [`f32ffeec763f0bdbf4bec25b52d654f77bff733d`](https://github.com/DrKLO/Telegram/commit/f32ffeec763f0bdbf4bec25b52d654f77bff733d), verified against upstream on 13 October 2026. This makes the first build reproducible; the exact commit is also saved in the artifact as `upstream-commit.txt`.

## Known limitations

- **No real GitHub Actions build has been run yet**, and the APK has not been installed or tested on a phone.
- Sample API credentials are for testing only and may be restricted by Telegram; this build is not a finished or reliable messaging client.
- Push notifications and other Google services still require RAZ's own Firebase / service configuration. Changing the package ID alone does not configure working push notifications.
- The APK is a test build, not a public release. Before distributing it, establish a release signing key, stable versioning, service configuration and a privacy policy.
- RAZ is an unofficial, independent client and must not be represented as an official Telegram product.

## License

The upstream Telegram for Android source is licensed under GPL-2.0-or-later. RAZ customization files are also provided under GPL-2.0-or-later. When distributing a modified client, comply with the upstream license and provide the corresponding source and required notices. See the upstream project: https://github.com/DrKLO/Telegram
