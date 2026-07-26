// Prints the phone's current LAN IPv4 address, or nothing if it can't be
// determined. Used by fileforge-launcher.sh to let Next.js's dev server
// accept requests from other devices on the same WiFi (allowedDevOrigins),
// without hardcoding an IP that changes whenever DHCP reassigns one.
const os = require("os");

const iface = Object.values(os.networkInterfaces())
  .flat()
  .find((i) => i && i.family === "IPv4" && !i.internal);

console.log(iface ? iface.address : "");
