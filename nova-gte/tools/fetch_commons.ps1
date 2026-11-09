# Download chosen Wikimedia Commons files (free licences) into reference/photos/commons2 with a licence/author index.
# Personal modelling reference; attribution kept in _licences.tsv. Run from the project root.
$UA = 'NovaGTE-reference/1.0 (personal modelling reference)'
$out = 'reference\photos\commons2'
New-Item -ItemType Directory -Force $out | Out-Null
$titles = @(
 'File:1985 Vauxhall Nova Sport (15834850432).jpg', 'File:1985 Vauxhall Nova Sport 1.3.jpg',
 'File:1985 Vauxhall Nova 1.3 SR (31829070875).jpg', 'File:1986 Vauxhall Nova 1.3 SR (26213792838).jpg',
 'File:1990 Vauxhall Nova 1.4 SR (14345187734).jpg', 'File:1990 Vauxhall Nova 1.4 SR (39181894635).jpg',
 'File:1990 Vauxhall Nova 1.4 SR (39376676234).jpg', 'File:Vauxhall Nova SRs (19470571825).jpg',
 'File:1990 Vauxhall Nova L 1.2 Front.jpg', 'File:1990 Vauxhall Nova L 1.2 Rear.jpg',
 'File:1989 (F) Vauxhall Nova.jpg', 'File:1989 Vauxhall Nova.jpg', 'File:Vauxhall Nova (12159800506).jpg',
 'File:Vauxhall Nova (29811229883).jpg', 'File:Vauxhallnova.jpg', 'File:1984 Vauxhall Nova.jpg',
 'File:1993 Vauxhall Nova GSi (44556077800).jpg', 'File:1993 Vauxhall Nova GSi (45649951634).jpg',
 'File:1993 Vauxhall Nova GSi (52862209249).jpg', 'File:1993 Vauxhall Nova GSi (53804837605).jpg',
 'File:1993 Vauxhall Nova GSi 1.6.jpg',
 'File:Festival of the Unexceptional 2019 (49802413408).jpg', 'File:Festival of the Unexceptional 2019 (49802486068).jpg',
 'File:Festival of the Unexceptional 2019 (49802965761).jpg', 'File:Festival of the Unexceptional 2019 (49802966286).jpg',
 'File:Festival of the Unexceptional 2019 (49803038776).jpg', 'File:Festival of the Unexceptional 2019 (49803038996).jpg',
 'File:Hagerty Classic Cars UK Festival of the Unexceptional 2017 - 35275863954.jpg',
 'File:Hagerty Classic Cars UK Festival of the Unexceptional 2017 - 36115882845.jpg',
 'File:Tempest Rally (216) (6564241673).jpg', 'File:Tempest Rally (217) (6564241315).jpg', 'File:Tempest Rally (487) (6564401195).jpg',
 'File:Forrestburn 27th June 2015-137 (19083245500).jpg', 'File:Forrestburn 27th June 2015-52 (19265040772).jpg'
)
$rows = @("file`tlicence`tauthor`tsource")
foreach ($t in $titles) {
  # Wikimedia answers 429 to scripted full-size downloads; their guidance is to take scaled thumbnails, slowly.
  $q = "https://commons.wikimedia.org/w/api.php?action=query&titles=$([uri]::EscapeDataString($t))&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=2400&format=json"
  try { $r = Invoke-RestMethod -UserAgent $UA $q } catch { "api refused: $t"; Start-Sleep -Seconds 30; continue }
  $p = $r.query.pages.PSObject.Properties.Value | Select-Object -First 1
  $ii = $p.imageinfo | Select-Object -First 1
  if (-not $ii) { "missing: $t"; continue }
  $name = ($t -replace '^File:', '') -replace '[\\/:*?"<>|]', '_'
  $dst = Join-Path $out $name
  $src = if ($ii.thumburl) { $ii.thumburl } else { $ii.url }
  if (-not (Test-Path $dst)) {
    $ok = $false
    foreach ($wait in 0, 20, 60) {
      Start-Sleep -Seconds $wait
      try { Invoke-WebRequest -UserAgent $UA $src -OutFile $dst -ErrorAction Stop; $ok = $true; break } catch { "  429/err, waiting..." }
    }
    if (-not $ok) { "FAILED: $name"; continue }
    Start-Sleep -Seconds 6
  }
  $lic = $ii.extmetadata.LicenseShortName.value; $art = ($ii.extmetadata.Artist.value -replace '<[^>]+>', '').Trim()
  $rows += "$name`t$lic`t$art`t$($ii.descriptionurl)"
  "{0,5}x{1,-5} {2,-14} {3}" -f $ii.width, $ii.height, $lic, $name
}
$rows | Set-Content (Join-Path $out '_licences.tsv') -Encoding UTF8
