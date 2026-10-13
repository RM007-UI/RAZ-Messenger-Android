#!/usr/bin/env python3
"""Apply RAZ branding to a checkout of the official Telegram Android source."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
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
    if not api_id_raw.isdigit() or int(api_id_raw) <= 0:
        raise SystemExit("TG_API_ID is missing or invalid; add it as a GitHub Actions secret")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        raise SystemExit("TG_API_HASH must be the 32-character value from my.telegram.org")

    gradle_props = upstream / "gradle.properties"
    vars_path = upstream / "TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java"
    strings_path = upstream / "TMessagesProj/src/main/res/values/strings.xml"
    manifest_path = upstream / "TMessagesProj/src/main/AndroidManifest.xml"
    app_gradle = upstream / "TMessagesProj_App/build.gradle"
    firebase_path = upstream / "TMessagesProj/google-services.json"
    required = (gradle_props, vars_path, strings_path, manifest_path, app_gradle, firebase_path)
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

    # This first target is the intended ARM64 device; other ABIs are not built yet.
    text = app_gradle.read_text(encoding="utf-8")
    text, count = re.subn(
        r'abiFilters\s+"armeabi-v7a",\s*"arm64-v8a",\s*"x86",\s*"x86_64"',
        'abiFilters "arm64-v8a"',
        text,
    )
    if count < 1:
        raise RuntimeError("Could not locate the upstream ABI filter list; refusing a partial patch")
    app_gradle.write_text(text, encoding="utf-8")

    manifest = manifest_path.read_text(encoding="utf-8")
    pattern = r'(<activity-alias\b(?:(?!>).)*?android:name="org\.telegram\.messenger\.DefaultIcon"(?:(?!>).)*?)(>)'

    def patch_alias(match: re.Match[str]) -> str:
        attrs = match.group(1)
        attrs = re.sub(r'\s+android:icon="[^"]*"', "", attrs)
        attrs = re.sub(r'\s+android:roundIcon="[^"]*"', "", attrs)
        attrs += ' android:icon="@drawable/raz_launcher" android:roundIcon="@drawable/raz_launcher"'
        return attrs + match.group(2)

    manifest, count = re.subn(pattern, patch_alias, manifest, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not locate DefaultIcon launcher alias in AndroidManifest.xml")
    manifest_path.write_text(manifest, encoding="utf-8")

    # Change only the upstream beta Firebase client; preserve the other client records.
    try:
        data = json.loads(firebase_path.read_text(encoding="utf-8"))
        matched = 0
        for client in data.get("client", []):
            app = client.get("client_info", {}).get("android_client_info", {})
            if app.get("package_name") == "org.telegram.messenger.beta":
                app["package_name"] = package_id + ".beta"
                matched += 1
        if matched != 1:
            raise RuntimeError(f"Expected one Firebase beta client; found {matched}")
        firebase_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"Could not safely update google-services.json: {exc}") from exc

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
