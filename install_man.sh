#!/data/data/com.termux/files/usr/bin/bash
mkdir -p $HOME/.local/share/man/man1
cp man/fileforge-*.1 $HOME/.local/share/man/man1/
echo "Run: man fileforge-cli"
