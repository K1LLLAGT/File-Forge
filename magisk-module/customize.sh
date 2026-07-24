#!/system/bin/sh
# FileForge Magisk installer hook. Runs at flash time in Magisk/KernelSU.
# Places the fileforge launcher into the module's system/bin so it is on PATH
# device-wide, and drops the Python package into the module data dir.

SKIPUNZIP=0

ui_print "*******************************"
ui_print "  FileForge — system installer "
ui_print "*******************************"

# Ensure the launcher is executable and lands on the system PATH overlay.
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/system/bin/fileforge" 0 0 0755

ui_print "- Installed fileforge -> /system/bin (Magisk overlay)"
ui_print "- Run 'fileforge list' from any shell after reboot"
ui_print "- Set FILEFORGE_LICENSE to unlock Pro features"
