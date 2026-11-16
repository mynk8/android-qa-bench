#!/usr/bin/env bash
# Build one data-access instrumentation APK per benchmark app (aqb.probe.<package>),
# signed with the same debug key as the app builds. SDK command-line tools only.
# Output: aqb/probe/out/probe-<package>.apk
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
JAR="$SDK/platforms/android-35/android.jar"
JDK="${AQB_JDK:-$HOME/.local/jdks/jdk17}"
KS="${AQB_KEYSTORE:-$HOME/.android/debug.keystore}"
OUT="$HERE/out"
rm -rf "$OUT" && mkdir -p "$OUT/classes" "$OUT/dex"

"$JDK/bin/javac" --release 11 -classpath "$JAR" -d "$OUT/classes" $(find "$HERE/src" -name '*.java')
JAVA_HOME="$JDK" "$BT/d8" --release --min-api 26 --lib "$JAR" --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')

for pkg in $(python3 -c "
import json,glob
for f in sorted(glob.glob('$ROOT/dataset/apps/*/app.json')): print(json.load(open(f))['package'])"); do
  m="$OUT/AndroidManifest-$pkg.xml"
  cat > "$m" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="aqb.probe.$pkg">
  <application android:hasCode="true" android:label="aqb probe" />
  <instrumentation android:name="aqb.probe.Probe" android:targetPackage="$pkg" android:label="aqb probe" />
</manifest>
EOF
  base="$OUT/probe-$pkg"
  "$BT/aapt2" link -o "$base.unaligned.apk" -I "$JAR" --manifest "$m" --min-sdk-version 26 --target-sdk-version 35
  python3 - "$base.unaligned.apk" "$OUT/dex/classes.dex" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "a", zipfile.ZIP_DEFLATED) as z:
    z.write(sys.argv[2], "classes.dex")
PY
  "$BT/zipalign" -f -p 4 "$base.unaligned.apk" "$base.aligned.apk"
  JAVA_HOME="$JDK" "$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
      --ks-key-alias androiddebugkey --out "$base.apk" "$base.aligned.apk"
  rm -f "$base.unaligned.apk" "$base.aligned.apk" "$base.apk.idsig"
  echo "built $(basename "$base.apk")"
done
