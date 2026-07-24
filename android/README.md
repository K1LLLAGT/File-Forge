# FileForge Android GUI (Monetization Strategy #2)

A thin native GUI over the FileForge engine. The heavy lifting stays in the
shared conversion engine; the app is a **file picker → format selector →
progress → share** shell, plus paid upsells (cloud conversion, OCR, batch,
unlimited).

## Architecture

```
┌─────────────────────────────────────────────┐
│  MainActivity (Compose UI)                    │
│  • Storage Access Framework file picker       │
│  • Format dropdown (from /v1/formats or local)│
│  • Progress bar + background WorkManager job   │
└───────────────┬───────────────────────────────┘
                │
        ┌───────▼─────────┐        ┌──────────────────────┐
        │ LocalEngine      │        │ CloudClient          │
        │ (Chaquopy Python │        │ Retrofit -> Cloud API │
        │  runs fileforge) │        │  (Pro/Cloud upsell)   │
        └──────────────────┘        └──────────────────────┘
```

- **On-device conversions** run the same Python `fileforge` package via
  [Chaquopy](https://chaquo.com/chaquopy/) (embeds CPython in the APK).
- **Cloud conversions / OCR / large video** call the FileForge Cloud API and
  are the primary in-app-purchase upsell.

## Monetization hooks

| Surface                | Free            | Pro (IAP / paid app)          |
|------------------------|-----------------|-------------------------------|
| Single-file convert    | ✅              | ✅                            |
| Batch / folder convert | ❌ (upsell)     | ✅                            |
| Cloud fallback + OCR    | ❌ (upsell)     | ✅ (uses Cloud API key)       |
| Ads                    | optional banner | removed                       |

Pricing (per spec): **$2.99–$9.99** on Google Play, **$4.99** on Amazon
Appstore, **$9.99** Pro. Upsells: cloud conversion, OCR, batch mode,
unlimited conversions.

## Build

Standard Gradle + Chaquopy. `app/src/main/python/` symlinks or copies
`../../src/fileforge`. See `app/MainActivity.kt` for the entry-point skeleton.
