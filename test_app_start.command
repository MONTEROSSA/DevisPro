#!/bin/bash
ROOT="/Users/ferdinandrothlisberger/devis-auto"
RES="$ROOT/DevisPro.app/Contents/Resources"
# module ins bundle
cp "$ROOT/devispro/app_gui.py" "$RES/devispro/"
cp "$ROOT/devispro/firmen_preise.py" "$RES/devispro/"
cp "$ROOT/devispro/importers/crbx_sia.py" "$RES/devispro/importers/"
cp "$ROOT/devispro/parsers/crb_sia.py" "$RES/devispro/parsers/"
cp "$ROOT/devispro/ch_preise.py" "$RES/devispro/"
echo "app_gui im bundle: $(grep -c 'DevisProApp' "$RES/devispro/app_gui.py")"
# start test (graceful, 4 sekunden, dann kill)
cd "$RES"
python3 devispro/app_gui.py > /tmp/gui_test.log 2>&1 &
GPID=$!
sleep 4
if kill -0 $GPID 2>/dev/null; then echo "GUI LAEUFT (pid $GPID) - kein crash in 4s"; else echo "GUI CRASH:"; cat /tmp/gui_test.log; fi
kill $GPID 2>/dev/null
echo "FERTIG"
