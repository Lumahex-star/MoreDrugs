param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\docs\branding")
)

$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "..\docs\branding\source-workshop.png"
if (-not (Test-Path -LiteralPath $source)) {
    throw "Missing source screenshot: $source"
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$cover = Join-Path $OutputDirectory "drug-expansion-cover-1920x1080.png"
magick $source `
    -resize 1920x1080^ -gravity center -extent 1920x1080 `
    -modulate 91,104,100 -contrast-stretch 0.25%x0.25% `
    -fill "rgba(2,5,12,0.12)" -draw "rectangle 0,0 1920,1080" `
    -font Impact -gravity Northwest `
    -fill "rgba(0,0,0,0.86)" -stroke "rgba(0,0,0,0.92)" -strokewidth 8 `
    -pointsize 174 -kerning 3 -annotate "+101+64" "DRUG" `
    -pointsize 174 -kerning 2 -annotate "+101+248" "EXPANSION" `
    -fill "#ead7a6" -stroke "#18150f" -strokewidth 5 `
    -pointsize 174 -kerning 3 -annotate "+88+51" "DRUG" `
    -pointsize 174 -kerning 2 -annotate "+88+235" "EXPANSION" `
    -strip -define png:compression-level=9 $cover

$icon = Join-Path $OutputDirectory "drug-expansion-icon-1024.png"
magick $source `
    -crop 1080x1080+340+0 +repage -resize 1024x1024 `
    -modulate 91,104,100 -contrast-stretch 0.25%x0.25% `
    -fill "rgba(2,5,12,0.12)" -draw "rectangle 0,0 1024,1024" `
    -font Impact -gravity Northwest `
    -fill "rgba(0,0,0,0.86)" -stroke "rgba(0,0,0,0.92)" -strokewidth 6 `
    -pointsize 126 -kerning 2 -annotate "+61+44" "DRUG" `
    -pointsize 126 -kerning 1 -annotate "+61+178" "EXPANSION" `
    -fill "#ead7a6" -stroke "#18150f" -strokewidth 4 `
    -pointsize 126 -kerning 2 -annotate "+52+35" "DRUG" `
    -pointsize 126 -kerning 1 -annotate "+52+169" "EXPANSION" `
    -strip -define png:compression-level=9 $icon

magick $icon -resize 512x512 -strip `
    (Join-Path $OutputDirectory "drug-expansion-icon-512.png")
