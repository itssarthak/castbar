#!/bin/sh
# Download counts per release. Homebrew installs fetch the same zip, so they're included.
gh api repos/itssarthak/castbar/releases --jq '.[] | "\(.tag_name)\t\([.assets[].download_count] | add // 0)"'
