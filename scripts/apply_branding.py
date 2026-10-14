#!/usr/bin/env python3
"""Apply RAZ branding to a checkout of the official Telegram Android source."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def one(pattern: str, replacement, text: str, label: str, flags: int = 0) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one match for {label}; found {count}. Upstream may have changed.")
    return result


def set_string(xml: str, name: str, value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return one(
        rf'(<string\s+name="{re.escape(name)}">).*?(</string>)',
        lambda match: match.group(1) + value + match.group(2),
        xml,
        f"string {name}",
        re.S,
    )


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: TG_API_ID=... TG_API_HASH=... python3 scripts/apply_branding.py [upstream-dir]")
        print("For a build-only test, set RAZ_ALLOW_UPSTREAM_TEST_API=1 and leave both TG_API_* variables empty.")
        return 0

    upstream = Path(sys.argv[1] if len(sys.argv) > 1 else "upstream").resolve()
    if not upstream.is_dir():
        raise SystemExit(f"Upstream checkout not found: {upstream}")

    brand = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))
    app_name = str(brand["app_name"]).strip()
    debug_name = str(brand["app_name_debug"]).strip()
    package_id = str(brand["package_id"]).strip()
    if not app_name or not debug_name:
        raise SystemExit("app_name and app_name_debug may not be empty")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+", package_id):
        raise SystemExit(f"Invalid Android application ID: {package_id!r}")

    api_id_raw = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    use_upstream_test_api = False

    if not api_id_raw and not api_hash:
        if os.environ.get("RAZ_ALLOW_UPSTREAM_TEST_API", "").strip() != "1":
            raise SystemExit(
                "TG_API_ID/TG_API_HASH are missing. For a test-only build, explicitly set "
                "RAZ_ALLOW_UPSTREAM_TEST_API=1; for a functional app, provide your own credentials."
            )
        use_upstream_test_api = True
        print("WARNING: Building with the upstream sample API credentials for testing only; do not distribute this APK.")
    elif not api_id_raw or not api_hash:
        raise SystemExit("TG_API_ID and TG_API_HASH must either both be set or both be empty")
    elif not api_id_raw.isdigit() or int(api_id_raw) <= 0:
        raise SystemExit("TG_API_ID is invalid")
    elif not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        raise SystemExit("TG_API_HASH must be the 32-character value from my.telegram.org")

    gradle_props = upstream / "gradle.properties"
    vars_path = upstream / "TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java"
    strings_path = upstream / "TMessagesProj/src/main/res/values/strings.xml"
    manifest_path = upstream / "TMessagesProj/src/main/AndroidManifest.xml"
    app_gradle = upstream / "TMessagesProj_App/build.gradle"
    # Telegram keeps Google Services configuration in both the app and library module.
    # The APK application module consumes TMessagesProj_App/google-services.json.
    firebase_paths = (
        upstream / "TMessagesProj/google-services.json",
        upstream / "TMessagesProj_App/google-services.json",
    )
    required = (gradle_props, vars_path, strings_path, manifest_path, app_gradle, *firebase_paths)
    missing = [str(path.relative_to(upstream)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Unexpected upstream source layout; missing: " + ", ".join(missing))

    text = gradle_props.read_text(encoding="utf-8")
    text = one(r"(?m)^APP_PACKAGE=.*$", f"APP_PACKAGE={package_id}", text, "APP_PACKAGE")
    gradle_props.write_text(text, encoding="utf-8")

    text = strings_path.read_text(encoding="utf-8")
    text = set_string(text, "AppName", app_name)
    text = set_string(text, "AppNameBeta", debug_name)
    strings_path.write_text(text, encoding="utf-8")

    text = vars_path.read_text(encoding="utf-8")
    if use_upstream_test_api:
        upstream_id = re.search(r"public static int APP_ID\s*=\s*(\d+)\s*;", text)
        upstream_hash = re.search(r'public static String APP_HASH\s*=\s*"([0-9a-fA-F]{32})"\s*;', text)
        if not upstream_id or int(upstream_id.group(1)) <= 0 or not upstream_hash:
            raise SystemExit("The pinned upstream source has no recognizable built-in test API credentials; refusing to build.")
    else:
        text = one(
            r"public static int APP_ID\s*=\s*\d+\s*;",
            f"public static int APP_ID = {int(api_id_raw)};",
            text,
            "BuildVars.APP_ID",
        )
        text = one(
            r'public static String APP_HASH\s*=\s*"[^"]*"\s*;',
            f'public static String APP_HASH = "{api_hash}";',
            text,
            "BuildVars.APP_HASH",
        )
    text = one(
        r"public static boolean CHECK_UPDATES\s*=\s*true\s*;",
        "public static boolean CHECK_UPDATES = false;",
        text,
        "BuildVars.CHECK_UPDATES",
    )
    text = one(
        r'"org\.telegram\.messenger\.beta"\.equals\(ApplicationLoader\.applicationContext\.getPackageName\(\)\)',
        f'"{package_id}.beta".equals(ApplicationLoader.applicationContext.getPackageName())',
        text,
        "BuildVars.isBetaApp package check",
    )
    text = one(
        r"public static boolean SUPPORTS_PASSKEYS\s*=\s*true\s*;",
        "public static boolean SUPPORTS_PASSKEYS = false;",
        text,
        "BuildVars.SUPPORTS_PASSKEYS",
    )
    vars_path.write_text(text, encoding="utf-8")

    # Build the two Android ARM ABIs we target: 32-bit ARMv7 and 64-bit ARM64.
    text = app_gradle.read_text(encoding="utf-8")
    text, count = re.subn(
        r'abiFilters\s+"armeabi-v7a",\s*"arm64-v8a",\s*"x86",\s*"x86_64"',
        'abiFilters "armeabi-v7a", "arm64-v8a"',
        text,
    )
    if count < 1:
        raise RuntimeError("Could not locate the upstream ABI filter list; refusing a partial patch")
    app_gradle.write_text(text, encoding="utf-8")

    manifest = manifest_path.read_text(encoding="utf-8")
    pattern = r'(<activity-alias\b(?:(?!>).)*?android:name="org\.telegram\.messenger\.DefaultIcon"(?:(?!>).)*?)(>)'

    def patch_alias(match: re.Match[str]) -> str:
        attrs = match.group(1)
        # activity-alias supports android:icon; roundIcon belongs on application.
        attrs = re.sub(r'\s+android:icon="[^"]*"', "", attrs)
        attrs = re.sub(r'\s+android:roundIcon="[^"]*"', "", attrs)
        attrs += ' android:icon="@drawable/raz_launcher"'
        return attrs + match.group(2)

    manifest, count = re.subn(pattern, patch_alias, manifest, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not locate DefaultIcon launcher alias in AndroidManifest.xml")
    manifest_path.write_text(manifest, encoding="utf-8")

    # Change the beta Firebase client in BOTH module config files. Google Services
    # processing runs for TMessagesProj_App, so updating only TMessagesProj is insufficient.
    for firebase_path in firebase_paths:
        try:
            data = json.loads(firebase_path.read_text(encoding="utf-8"))
            matched = 0
            for client in data.get("client", []):
                app = client.get("client_info", {}).get("android_client_info", {})
                if app.get("package_name") == "org.telegram.messenger.beta":
                    app["package_name"] = package_id + ".beta"
                    matched += 1
            if matched != 1:
                raise RuntimeError(
                    f"{firebase_path.relative_to(upstream)}: expected one Firebase beta client; found {matched}"
                )
            firebase_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"Could not safely update {firebase_path.relative_to(upstream)}: {exc}") from exc

    # RAZ visual refresh: iOS-inspired dark materials, pinned fonts, and Arabic fallback.
    font_commit = "66928797f271fed5ee428544e7229685e2d90127"
    font_resource_dir = upstream / "TMessagesProj/src/main/res/font"
    font_resource_dir.mkdir(parents=True, exist_ok=True)
    font_sources = (
        (
            "Inter variable font",
            f"https://raw.githubusercontent.com/google/fonts/{font_commit}/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
            font_resource_dir / "raz_inter.ttf",
        ),
        (
            "Noto Sans Arabic variable font",
            f"https://raw.githubusercontent.com/google/fonts/{font_commit}/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf",
            font_resource_dir / "raz_noto_arabic.ttf",
        ),
    )
    for font_label, font_url, font_path in font_sources:
        try:
            with urllib.request.urlopen(font_url, timeout=120) as response:
                font_bytes = response.read()
        except Exception as exc:
            raise RuntimeError(f"Could not download pinned {font_label}") from exc
        if len(font_bytes) < 100_000 or font_bytes[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
            raise RuntimeError(f"Downloaded {font_label} did not look like a valid TrueType/OpenType font")
        font_path.write_bytes(font_bytes)

    font_license_dir = upstream / "TMessagesProj/src/main/assets"
    font_license_dir.mkdir(parents=True, exist_ok=True)
    for license_name, license_url in (
        (
            "RAZ-Inter-OFL.txt",
            f"https://raw.githubusercontent.com/google/fonts/{font_commit}/ofl/inter/OFL.txt",
        ),
        (
            "RAZ-Noto-Sans-Arabic-OFL.txt",
            f"https://raw.githubusercontent.com/google/fonts/{font_commit}/ofl/notosansarabic/OFL.txt",
        ),
    ):
        try:
            with urllib.request.urlopen(license_url, timeout=60) as response:
                license_text = response.read().decode("utf-8")
        except Exception as exc:
            raise RuntimeError(f"Could not download font license {license_name}") from exc
        if "SIL OPEN FONT LICENSE Version 1.1" not in license_text:
            raise RuntimeError(f"Unexpected license content for {license_name}")
        (font_license_dir / license_name).write_text(license_text, encoding="utf-8")

    # Set the font for standard Android widgets while retaining Android's own fallback for
    # glyphs not covered by Inter. Canvas-based text will use Inter with Noto Sans Arabic fallback.
    styles_path = upstream / "TMessagesProj/src/main/res/values/styles.xml"
    styles = styles_path.read_text(encoding="utf-8")
    styles, count = re.subn(
        r'(<style name="MyTextViewStyle"[^>]*>\s*)',
        r'\1        <item name="android:fontFamily">@font/raz_inter</item>\n',
        styles,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not attach Inter to MyTextViewStyle")
    styles, count = re.subn(
        r'(<style name="EditTextNoBackgroundStyle"[^>]*>\s*)',
        r'\1        <item name="android:fontFamily">@font/raz_inter</item>\n',
        styles,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not attach Inter to EditTextNoBackgroundStyle")

    # Avoid a white flash during launch; keep the initial surface consistent with RAZ dark mode.
    for style_name in ("Theme.TMessages.Start", "Theme.TMessages"):
        for item_name in ("android:colorBackground", "android:windowBackground"):
            pattern = (
                r'(<style name="' + re.escape(style_name) + r'".*?<item name="' +
                re.escape(item_name) + r'">)@android:color/white(</item>)'
            )
            styles, count = re.subn(pattern, r'\1#FF0B0D12\2', styles, count=1, flags=re.S)
            if count != 1:
                raise RuntimeError(f"Could not set dark launch surface {style_name}/{item_name}")
    styles_path.write_text(styles, encoding="utf-8")

    # Default to Telegram's existing dark theme only when the user has not chosen a theme.
    theme_java_path = upstream / "TMessagesProj/src/main/java/org/telegram/ui/ActionBar/Theme.java"
    theme_java = theme_java_path.read_text(encoding="utf-8")
    theme_java = one(
        r'String theme = preferences\.getString\("theme", null\);',
        'String theme = preferences.getString("theme", "Dark");',
        theme_java,
        "RAZ first-run dark theme default",
    )
    theme_java_path.write_text(theme_java, encoding="utf-8")

    # The pinned upstream already includes a blur-backed glass tab bar. Tune its dark glass
    # palette rather than adding costly blur layers throughout the message content.
    def signed_argb(color_hex: str) -> str:
        value = int(color_hex, 16)
        if value >= 0x80000000:
            value -= 0x100000000
        return str(value)

    palette = {
        "windowBackgroundWhite": "FF0B0D12",
        "windowBackgroundGray": "FF07080C",
        "windowBackgroundChecked": "FF1B1E26",
        "actionBarDefault": "FF10131A",
        "actionBarDefaultTitle": "FFF5F7FC",
        "actionBarDefaultIcon": "FFF5F7FC",
        "actionBarDefaultSearch": "FFE8ECF5",
        "actionBarDefaultSubtitle": "FFA0A7B4",
        "actionBarDefaultSubmenuBackground": "FF1B1E26",
        "windowBackgroundWhiteBlackText": "FFF1F3F8",
        "windowBackgroundWhiteGrayText": "FFA1A8B5",
        "windowBackgroundWhiteGrayText2": "FF9098A7",
        "windowBackgroundWhiteGrayText3": "FF7D8594",
        "windowBackgroundWhiteGrayIcon": "FF858D9B",
        "windowBackgroundWhiteBlueText": "FF0A84FF",
        "windowBackgroundWhiteLinkText": "FF64A9FF",
        "dialogTextBlue": "FF0A84FF",
        "dialogBackground": "FF191C24",
        "dialogBackgroundGray": "FF252832",
        "divider": "FF292D36",
        "chats_name": "FFF1F3F8",
        "chats_nameMessage": "FFA1A8B5",
        "chats_nameMessage_threeLines": "FFA1A8B5",
        "chats_unreadCounter": "FF0A84FF",
        "telegram_color": "FF0A84FF",
        "chat_outBubbleSelected": "FF0769D8",
        "chat_inBubbleSelected": "FF303746",
        "chats_actionBackground": "FF222630",
        "chat_inBubble": "FF252934",
        "chat_inBubbleSelected": "FF303745",
        "chat_outBubble": "FF0A84FF",
        "chat_messageTextIn": "FFF1F3F8",
        "chat_messageTextOut": "FFFFFFFF",
        "chat_messagePanelBackground": "FF171A21",
        "chat_messagePanelHint": "FF8F97A6",
        "chat_messagePanelVoiceBackground": "FF20242D",
        "chat_topPanelLine": "FF2B303A",
        "glass_defaultIcon": "DFF5F7FC",
        "glass_defaultText": "DFF5F7FC",
        "glass_targetMainTabs": "B81A1D25",
        "glass_targetMainTopPanel": "B8181B22",
    }
    for theme_asset in (
        upstream / "TMessagesProj/src/main/assets/darkblue.attheme",
        upstream / "TMessagesProj/src/main/assets/night.attheme",
    ):
        if not theme_asset.is_file():
            raise RuntimeError(f"Missing dark theme asset: {theme_asset.name}")
        source_lines = theme_asset.read_text(encoding="utf-8").splitlines()
        seen = set()
        result_lines = []
        for line in source_lines:
            if "=" in line:
                key = line.split("=", 1)[0]
                if key in palette:
                    line = key + "=" + signed_argb(palette[key])
                    seen.add(key)
            result_lines.append(line)
        for palette_key, palette_value in palette.items():
            if palette_key not in seen:
                result_lines.append(palette_key + "=" + signed_argb(palette_value))
        required_colors = {"windowBackgroundWhite", "actionBarDefault", "actionBarDefaultTitle", "windowBackgroundWhiteBlackText"}
        missing_colors = sorted(required_colors - seen)
        if missing_colors:
            raise RuntimeError(f"{theme_asset.name} is missing expected color keys: {', '.join(missing_colors)}")
        theme_asset.write_text("\n".join(result_lines) + "\n", encoding="utf-8")

    # iMessage-inspired message shapes: fuller capsule corners, keeping grouped-message joins.
    bubble_path = upstream / "TMessagesProj/src/main/java/org/telegram/ui/ActionBar/MessageDrawable.java"
    bubble_source = bubble_path.read_text(encoding="utf-8")
    bubble_source, count = re.subn(
        r'newRad = dp\(SharedConfig\.bubbleRadius\);',
        'newRad = dp(Math.max(20, SharedConfig.bubbleRadius));',
        bubble_source,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not locate the cached message bubble radius")
    radius_pattern = (
        r'(?m)^([ \t]*)rad = dp\(SharedConfig\.bubbleRadius\);\n'
        r'\1nearRad = dp\(Math\.min\(6, SharedConfig\.bubbleRadius\)\);'
    )
    bubble_source, count = re.subn(
        radius_pattern,
        lambda match: match.group(1) + 'rad = dp(Math.max(20, SharedConfig.bubbleRadius));\n'
            + match.group(1) + 'nearRad = dp(12);',
        bubble_source,
    )
    if count < 2:
        raise RuntimeError(f"Expected both standard message bubble radius paths; found {count}")
    bubble_path.write_text(bubble_source, encoding="utf-8")

    # Give the input row an iOS-like pill surface with a subtle cool border.
    # The existing send/attachment/emoji handlers and layout remain intact.
    compose_path = upstream / "TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java"
    compose_source = compose_path.read_text(encoding="utf-8")
    compose_anchor = (
        r'(        frameLayout\.setClipChildren\(false\);\n)'
        r'(        textFieldContainer\.addView\(frameLayout, LayoutHelper\.createFrame\(LayoutHelper\.MATCH_PARENT)'
    )
    compose_replacement = (
        r'\1'
        '        android.graphics.drawable.GradientDrawable razComposeBackground = '
        'new android.graphics.drawable.GradientDrawable();\n'
        '        razComposeBackground.setColor(Color.argb(236, 28, 32, 42));\n'
        '        razComposeBackground.setCornerRadius(dp(23));\n'
        '        razComposeBackground.setStroke(dp(1), Color.argb(42, 220, 230, 248));\n'
        '        frameLayout.setBackground(razComposeBackground);\n'
        r'\2'
    )
    compose_source, count = re.subn(compose_anchor, compose_replacement, compose_source, count=1)
    if count != 1:
        raise RuntimeError("Could not attach the RAZ pill-style compose background")
    compose_path.write_text(compose_source, encoding="utf-8")

    # Build a composite typeface on Android 10+ so Latin uses Inter and Arabic-script text
    # (including Persian) prefers Noto Sans Arabic; older Android releases fall back safely.
    utilities_path = upstream / "TMessagesProj/src/main/java/org/telegram/messenger/AndroidUtilities.java"
    utilities = utilities_path.read_text(encoding="utf-8")
    if "import android.graphics.fonts.Font;" not in utilities:
        utilities = utilities.replace(
            "import android.graphics.Typeface;\n",
            "import android.graphics.Typeface;\nimport android.graphics.fonts.Font;\nimport android.graphics.fonts.FontFamily;\n",
            1,
        )
    if "private static Typeface razTypeface;" not in utilities:
        utilities = utilities.replace(
            "public static Typeface mediumTypeface;\n",
            "public static Typeface mediumTypeface;\n    private static Typeface razTypeface;\n",
            1,
        )
    helper = r'''
    private static Typeface getRazTypeface() {
        if (razTypeface != null) {
            return razTypeface;
        }
        synchronized (AndroidUtilities.class) {
            if (razTypeface == null) {
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        Font latinFont = new Font.Builder(ApplicationLoader.applicationContext.getResources(), R.font.raz_inter)
                                .setWeight(400)
                                .build();
                        Font arabicFont = new Font.Builder(ApplicationLoader.applicationContext.getResources(), R.font.raz_noto_arabic)
                                .setWeight(400)
                                .build();
                        FontFamily latinFamily = new FontFamily.Builder(latinFont).build();
                        FontFamily arabicFamily = new FontFamily.Builder(arabicFont).build();
                        razTypeface = new Typeface.CustomFallbackBuilder(latinFamily)
                                .addCustomFallback(arabicFamily)
                                .setSystemFallback("sans-serif")
                                .build();
                    } else {
                        razTypeface = Typeface.create("sans-serif", Typeface.NORMAL);
                    }
                } catch (Throwable error) {
                    FileLog.e(error);
                    razTypeface = Typeface.create("sans-serif", Typeface.NORMAL);
                }
            }
        }
        return razTypeface;
    }

'''
    if "private static Typeface getRazTypeface()" not in utilities:
        utilities, count = re.subn(
            r'(?m)^    public static Typeface bold\(\) \{',
            helper + '    public static Typeface bold() {',
            utilities,
            count=1,
        )
        if count != 1:
            raise RuntimeError("Could not add RAZ composite typeface helper")

    old_bold = r'''    public static Typeface bold() {
        if (mediumTypeface == null) {
            if (SharedConfig.useSystemBoldFont && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                mediumTypeface = Typeface.create(null, 500, false);
            } else {
                mediumTypeface = getTypeface(TYPEFACE_ROBOTO_MEDIUM);
            }
        }
        return mediumTypeface;
    }'''
    new_bold = r'''    public static Typeface bold() {
        if (mediumTypeface == null) {
            if (SharedConfig.useSystemBoldFont && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                mediumTypeface = Typeface.create(getRazTypeface(), 500, false);
            } else {
                mediumTypeface = Typeface.create(getRazTypeface(), Typeface.BOLD);
            }
        }
        return mediumTypeface;
    }'''
    if old_bold in utilities:
        utilities = utilities.replace(old_bold, new_bold, 1)
    elif new_bold not in utilities:
        raise RuntimeError("Could not switch canvas bold text to the RAZ font family")

    get_typeface_anchor = "public static Typeface getTypeface(String assetPath) {\n        synchronized (typefaceCache) {"
    get_typeface_replacement = """public static Typeface getTypeface(String assetPath) {
        synchronized (typefaceCache) {
            if (TYPEFACE_ROBOTO_MEDIUM.equals(assetPath)) {
                if (!typefaceCache.containsKey(assetPath)) {
                    typefaceCache.put(assetPath, Typeface.create(getRazTypeface(), Typeface.BOLD));
                }
                return typefaceCache.get(assetPath);
            }"""
    if get_typeface_anchor in utilities:
        utilities = utilities.replace(get_typeface_anchor, get_typeface_replacement, 1)
    elif get_typeface_replacement not in utilities:
        raise RuntimeError("Could not redirect Telegram's shared medium typeface to RAZ fonts")
    utilities_path.write_text(utilities, encoding="utf-8")

    icon_src = ROOT / "assets/icons/raz_launcher.xml"
    icon_dst = upstream / "TMessagesProj/src/main/res/drawable/raz_launcher.xml"
    if not icon_src.is_file():
        raise SystemExit(f"Missing bundled vector icon: {icon_src}")
    icon_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_src, icon_dst)

    print(f"Applied RAZ branding to {upstream}")
    print(f"Debug application ID: {package_id}.beta")
    print("API credential values were not printed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
