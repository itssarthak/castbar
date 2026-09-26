#!/bin/sh
# Usage: scripts/release.sh 0.2.0
set -eu
V=${1:?version, e.g. 0.2.0}
cd "$(dirname "$0")/.."
sed -i '' "s/\"CFBundleShortVersionString\": \"[^\"]*\"/\"CFBundleShortVersionString\": \"$V\"/" setup.py
rm -rf build dist
.venv/bin/python setup.py py2app >/dev/null
ZIP="dist/Castbar-$V.zip"
ditto -c -k --keepParent dist/Castbar.app "$ZIP"
SHA=$(shasum -a 256 "$ZIP" | cut -d' ' -f1)
git commit -am "Release $V" || true
git tag "v$V" && git push && git push --tags
gh release create "v$V" "$ZIP" --title "Castbar $V" --generate-notes

TAP=$(mktemp -d)
gh repo clone itssarthak/homebrew-tap "$TAP" -- -q
sed -i '' "s/version \"[^\"]*\"/version \"$V\"/; s/sha256 \"[^\"]*\"/sha256 \"$SHA\"/" "$TAP/Casks/castbar.rb"
git -C "$TAP" commit -qam "castbar $V" && git -C "$TAP" push -q
echo "Released $V ($SHA)"
