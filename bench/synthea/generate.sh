#!/bin/sh
# usage: bench/synthea/generate.sh <absolute output folder>
set -eu

here=$(cd "$(dirname "$0")" && pwd)
out=$1
python=${PYTHON:-python3}

image=eclipse-temurin:21-jre@sha256:cff19e6215689161eb6162c11b86b0c60ddf802164f2eaf48d570f8fb79a36c5
jar_sha256=ed43c20ad40ba5c3bc724503a5af032715fe3c491620b766148e7c2361e6ecc1
jar_url=https://github.com/synthetichealth/synthea/releases/download/v4.0.0/synthea-with-dependencies.jar
blanche_hermiston=18a08f42-e19d-3072-8737-90a26ea0cb6d
xochitl_corkery=a8b18ea4-466a-da66-fd0e-20dbd1de56c5

mkdir -p "$out"
started=$(date +%s)

MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$here:/synthea:ro" \
  -v "$out:/out" \
  "$image" \
  bash -c "set -eu
    curl -sSL -o /tmp/synthea.jar $jar_url
    echo '$jar_sha256  /tmp/synthea.jar' | sha256sum -c -
    for run in ten-years lifetime; do
      java -jar /tmp/synthea.jar -c /synthea/\$run.properties --exporter.baseDirectory=/out/\$run \
        -s 90 -cs 90 -r 20261001 -e 20261001 -p 40 -a 45-80 Washington
    done"

echo "synthea seconds $(($(date +%s) - started))"

$python "$here/../generate/synthea_person.py" "$out/ten-years" "$blanche_hermiston" "$out/synthea-10y-18a08f42.xml.gz"
$python "$here/../generate/synthea_person.py" "$out/lifetime" "$xochitl_corkery" "$out/synthea-lifetime-a8b18ea4.json.gz"
