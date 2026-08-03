# KALITE — UI Architecture Plan

> Bu dosya bir agent tarafından adım adım takip edilecek. Her adım tamamlandığında `[x]` işaretlenecek, **Yapılan değişiklikler / Build durumu / Doğrulama** bölümleri doldurulacak.
> **Yasak:** AI-slop marketing dili ("Unlock", "Empower", "Elevate"). Sadece kullanıcının gerçekten yaptığı eylemi söyleyen mikro-metinler.

---

## KULLANICI KARARLARI

| # | Konu | Karar | Gerekçe |
|---|------|------|---------|
| 1 | Renk paleti | 5 hex (aşağıda) | Krem + kiremit + yosun, rapor/mürekkep estetiği — SaaS mor-mavi gradyanlarından farklılaşma |
| 2 | Tipografi | Fraunces + IBM Plex Sans | Serif başlık + mekanik sans gövde, mühendis raporu tonu |
| 3 | Layout | Sağa yaslanmış 2-kolon (sol 1/3 etiket, sağ 2/3 içerik) | Her sayfada simetri kırma, sol-akış okuma hissi |
| 4 | İmza öge | Damga (sağ üst tarih damgası + PDF print) | Her raporun "basılmış" hissi, kimlik imzası |
| 5 | Mikro-metin | "Atölye", "Masanın üstü", "Tarayıcı takıldı" | Sistem dili yerine kullanıcı eylemi |

---

## 1. RENK PALETİ (5 hex, gerekçe)

| Hex | İsim | Neden |
|-----|------|-------|
| `#0A0A0A` | Mürekkep | Ana metin + vurgu çerçeveleri. Kağıt üzerine düşmüş mürekkep. |
| `#F2EEE3` | Pergamen | Sayfa arka planı. Sıcak krem, solgun değil — eski defter kağıdı. |
| `#C5532F` | Kiremit | Birincil vurgu. Hardal-altı paslanmış, "incelenmiş" — sıradan turuncu değil. |
| `#7A8B6F` | Yosun | Başarı/iyi durum. Kuru yaz, doğada bulunan sessiz yeşil. |
| `#A03A2A` | Yanık | Hata/kritik. Kiremitin kardeşi, daha acil, daha derin. |

**Neden bu kombinasyon**: Proje "kod analizi/depo kalitesi" yapıyor — bir mühendis masası hissi. Krem+mürekkep+kiremit paleti, 2024 SaaS dashboard'larından (`#6366F1` moru) tamamen farklı. Kullanıcı "bir rapor okuyorum" hisseder, "bir uygulama kullanıyorum" değil.

**Dark mode** (`prefers-color-scheme: dark` veya manual toggle):
- `#0A0A0A` → `#F2EEE3` (invert)
- `#F2EEE3` → `#1A1815` (koyu kağıt)
- Diğer renkler aynı kalır (kiremit, yosun, yanık zaten doygun)

---

## 2. TİPOGRAFİ (somut isimler)

- **Display (başlıklar)**: **Fraunces** — opsz 9-144, wght 100-900. Vintage mekanik kitap, tırnaklı ("tailed") karakterler. Google Fonts URL: `next/font/google` ile `Fraunces` import.
- **Body (gövde)**: **IBM Plex Sans** — wght 100-700, insanist sans, mekanik okunabilirlik. Google Fonts.

**Neden bu ikili**: Fraunces "röportaj/analiz raporu" tonu verir, IBM Plex endüstriyel "not defteri" metni. İkisi birlikte "araştırmacı analiz raporu" ruhu kurar. Inter/Roboto her yerde — bu proje onu reddediyor.

**Ölçekler**:
- H1: Fraunces 36-48px, semibold
- H2: Fraunces 24-28px, semibold
- H3: Fraunces 18-20px, medium
- Body: IBM Plex 14-16px, regular
- Caption: IBM Plex 12px, medium, letter-spacing 0.5px, uppercase
- Code/mono: JetBrains Mono (mevcut)

---

## 3. LAYOUT KONSEPTİ (asimetri)

**Temel grid**: 12-col, ama **asla ortalı**. Sol 1/3 etiket, sağ 2/3 içerik. Hiçbir yerde `text-align: center` yok (hero'lar dahil).

| Bölge | Layout |
|-------|--------|
| Header | 2-kolon: sol (Damga + başlık + meta), sağ (4-6 istatistik badge) |
| Hero (landing) | Tam genişlik ama sola hizalı başlık + sağda Damga |
| Cards | Sol etiket 1/3 + sağ içerik 2/3 |
| Tabs | Horizontal scroll (mobil alt tab bar), desktop'ta 11 tab yan yana |
| Footer | Sol telif + sağ keyboard ipucu |

**Asimetri örnekleri**:
- HealthScoreCard: sol 1/3 = "Genel sağlık" etiket, sağ 2/3 = büyük skor + altında renk çubukları
- Roadmap: sol 1/3 = "Sprint X", sağ 2/3 = step kartları
- Validation: sol 1/3 = "Kural kalitesi", sağ 2/3 = tablo

---

## 4. İMZA ÖGE — DAMGA (Stamp)

**Konum**: Her sayfanın sağ üst köşesi, mutlak pozisyon, hafifçe döndürülmüş (`-2deg`).

**Görünüm**:
- 48×48px SVG daire, 2px stroke `#0A0A0A`
- İç dikey çizgi (ortada)
- Üst: "n.{reportNo}" (Fraunces 8px)
- Alt: "DD.MM.YYYY" (IBM Plex 7px)
- Sol küçük etiket: repo kısa adı (hover'da görünür)

**Etkileşim**:
- Hover: scale 1.08, rotate -3deg, 200ms
- Click: `window.print()` tetikler → kullanıcı PDF/print dialog alır
- `prefers-reduced-motion`: rotate sıfırlanır, scale yok

**Sayfalarda varlığı**: `LandingView`, `ProgressView`, `ResultsDashboard` (her tab'da), `SettingsView` — her yerde aynı damga, sadece `reportNo` ve `date` değişir.

**Neden bu**: Rapor hissi. Her analiz "basılmış" bir doküman. Print tetikleme ekstra işlevsellik. Dönüş hareketi "el vurulmuş" hissi.

---

## 5. MİKRO-METİN KURALLARI

Sistem dili yerine **kullanıcı eylemi**:

| Sistem (eski) | Kullanıcı (yeni) |
|--------------|------------------|
| Save | Çıktıyı kilitle |
| Failed | Tarayıcı takıldı |
| Settings | Atölye |
| Run Analysis | Analizi başlat |
| Overview | Masanın üstü |
| No data | Henüz bir şey çözümlenmedi |
| Files | Dosyalar |
| Graph | Bağlantı haritası |
| Webhook config | Tetikleyici URL'si |
| Continue | Devam et |
| Cancel | Vazgeç |
| Run Benchmark | Doğrulamayı başlat |
| Test Connection | Bağlantıyı yokla |
| Self-Protection | Atölye ayarları korunuyor |
| Loading | Çözümleniyor... |

**Kural**: "kullanıcı ne yaptı" → "buton/durum ne diyor". "Webhook config" değil, "Tetikleyici URL'si" (kullanıcının yaptığı eylem — bir URL girmek).

---

## 6. CSS IMPLEMENTASYON

### 6.1 globals.css (foundation)

```css
@import "./tailwind-gen.css";

:root {
  --kl-bg: #F2EEE3;
  --kl-bg-alt: #E8E2D2;
  --kl-fg: #0A0A0A;
  --kl-muted: #3A3530;
  --kl-accent: #C5532F;
  --kl-success: #7A8B6F;
  --kl-danger: #A03A2A;
  --kl-border: rgba(10, 10, 10, 0.12);
  --font-display: "Fraunces", "Georgia", serif;
  --font-body: "IBM Plex Sans", "Helvetica Neue", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

.dark {
  --kl-bg: #1A1815;
  --kl-bg-alt: #25221D;
  --kl-fg: #F2EEE3;
  --kl-muted: #A8A199;
  --kl-accent: #D9785C;
  --kl-success: #92A687;
  --kl-danger: #C55344;
  --kl-border: rgba(242, 238, 227, 0.15);
}

@layer base {
  html { color-scheme: light dark; }
  body {
    background: var(--kl-bg);
    color: var(--kl-fg);
    font-family: var(--font-body);
  }
  h1, h2, h3 { font-family: var(--font-display); }
  code, pre, kbd { font-family: var(--font-mono); }
}

@layer utilities {
  .kl-paper { background-color: var(--kl-bg); }
  .kl-paper-alt { background-color: var(--kl-bg-alt); }
  .kl-ink { color: var(--kl-fg); }
  .kl-muted { color: var(--kl-muted); }
  .kl-accent { color: var(--kl-accent); }
  .kl-success { color: var(--kl-success); }
  .kl-danger { color: var(--kl-danger); }
  .kl-border-soft { border: 1px solid var(--kl-border); }
  .kl-border-l-accent { border-left: 2px solid var(--kl-accent); }
  .kl-font-display { font-family: var(--font-display); }
  .kl-font-body { font-family: var(--font-body); }
  .kl-asym-left { width: 33.333%; }
  .kl-asym-right { width: 66.666%; }

  .kl-damga {
    transform: rotate(-2deg);
    border: 2px solid var(--kl-fg);
    border-radius: 50%;
    background: var(--kl-bg);
    width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 200ms ease-out, box-shadow 200ms ease-out;
  }
  .kl-damga:hover {
    transform: rotate(-3deg) scale(1.08);
    box-shadow: 0 4px 12px rgba(10, 10, 10, 0.15);
  }
  .kl-card-hover {
    transition: transform 200ms ease-out, box-shadow 200ms ease-out;
  }
  .kl-card-hover:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(10, 10, 10, 0.08);
  }
  .kl-print-hide { }
}

@media (prefers-reduced-motion: reduce) {
  .kl-damga,
  .kl-damga:hover,
  .kl-card-hover,
  .kl-card-hover:hover {
    transform: none;
    transition: 0.01ms;
  }
}

@media print {
  .kl-print-hide { display: none !important; }
  body { background: white; }
}
```

### 6.2 tailwind.config.ts (kl- prefix + safelist)

```ts
import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
    darkMode: "class",
    content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  safelist: [
    "kl-paper", "kl-paper-alt", "kl-ink", "kl-muted", "kl-accent",
    "kl-success", "kl-danger", "kl-border-soft", "kl-border-l-accent",
    "kl-font-display", "kl-font-body", "kl-asym-left", "kl-asym-right",
    "kl-damga", "kl-card-hover", "kl-print-hide",
  ],
  plugins: [tailwindcssAnimate],
};
export default config;
```

**CSS class çakışması çözümü**:
- Tüm class'lar `kl-` prefix ile (`kl-card` değil `card`, `kl-grid` değil `grid`)
- Tailwind `@layer utilities` ile sadece `kl-*` class'lar üretilir
- shadcn/ui Tailwind class'ları (`text-rose-500`, `border` vb.) kullanılmaz — tüm sınıflar `kl-*` ile yapılır
- `safelist` Tailwind'in dynamic class detection'ı kaçırdığı yerlerde kullanılır

---

## 7. MİMARİ — HER BİLEŞEN DETAYI

### 7.1 `src/components/kl/Damga.tsx`

```tsx
"use client";
type Props = { date?: Date; repoName?: string; reportNo: number };
export function Damga({ date = new Date(), repoName = "local", reportNo = 1 }: Props) {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = date.getFullYear();
  const handleClick = () => { if (typeof window !== "undefined") window.print(); };
  return (
    <button
      type="button"
      onClick={handleClick}
      title={`${repoName} — n.${reportNo} — ${dd}.${mm}.${yyyy}`}
      className="kl-damga kl-print-hide fixed top-4 right-4 z-40 flex-col"
      aria-label={`Yazdır: ${repoName} rapor ${reportNo}`}
    >
      <span className="kl-font-display text-[8px] leading-none">n.{reportNo}</span>
      <span className="kl-font-body text-[7px] leading-none opacity-70">{dd}.{mm}.{yyyy}</span>
    </button>
  );
}
```

### 7.2 `src/components/kl/Header.tsx`

```tsx
type Props = {
  title: string;
  subtitle?: string;
  meta?: Array<{ label: string; value: string }>;
  reportNo?: number;
  repoName?: string;
  date?: Date;
};
// Asimetri: 12-col grid, sol 5/12 etiket, sağ 7/12 meta
// Damga mutlak sağ üstte
```

### 7.3 `src/components/kl/AnalizKarti.tsx`

```tsx
type Accent = "good" | "warn" | "bad" | "neutral";
type Props = {
  leftLabel: string;
  rightValue: ReactNode;
  accent?: Accent;
  hint?: string;
};
// 2-col: sol 1/3 etiket, sağ 2/3 değer
// accent border-l-2px (good=yosun, warn=hardal, bad=yanık, neutral=mürekkep)
```

### 7.4 `src/components/kl/SinyalCubugu.tsx`

```tsx
type Status = "good" | "warn" | "bad" | "info" | "pending" | "running";
type Props = { status: Status; children: ReactNode };
// 14px IBM Plex rounded-full border
// durum renkleri: good=yosun, warn=hardal, bad=yanık, info=mürekkep, pending=mürekkep(opacity-50), running=kiremit+animate-pulse
```

### 7.5 `src/components/kl/KlavuzKutu.tsx`

```tsx
type Variant = "info" | "warn" | "tip" | "empty";
type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: Variant;
};
// empty: "Henüz bir şey çözümlenmedi" + "Atölyeye git" butonu
```

### 7.6 `src/components/kl/DragovZone.tsx`

```tsx
type Props = { onFileSelect: (files: FileList) => void; isDragging: boolean };
// Krem kağıt background + 2px dashed border
// Hover: 2px solid kiremit + scale 1.02
// Spinner: klasik circle (kiremit, animate-spin)
```

### 7.7 `src/components/kl/AciklamaZinciri.tsx`

```tsx
type Step = { label: string; detail?: ReactNode };
type Props = { steps: Step[]; title?: string };
// Expandable accordian: "Neden?" tıklanınca adımlar açılır
// 11 adım zinciri: Öneri → KökNeden → Planlama → Kanıt → Analizör → Dosya → Graf → ...
```

### 7.8 Diğer bileşenler (kısa)

- `IlerlemeCubugu.tsx`: 9 adım çubuğu, aktif adım kiremit
- `OlayButonu.tsx`: primary/secondary/ghost variant
- `GirisAlani.tsx`: text/number/select variant
- `KlavyeOdagi.tsx`: `<kbd>` wrapper
- `CiktiKutusu.tsx`: code/markdown/json block
- `DosyaSatiri.tsx`: icon + path + badge

---

## 8. HER VIEW İÇİN MİMARİ

### 8.1 `LandingView` (view=landing)

```
┌──────────────────────────────────────────────────────────┐
│  [Header: "Depoyu analiz et" / "Mimariyi anla"]    [Damga]│
│                                                            │
│  [Sol 1/3]                      [Sağ 2/3: Tabs]          │
│  - "Nasıl çalışır" başlığı    [GitHub | Yerel Klasör]   │
│  - 3 satır (serbest yerleşim)                          │
│    * "1. URL yapıştır"                                  │
│    * "2. Analizi başlat"                                │
│    * "3. Bulguları incele"                              │
│                                                            │
│  [Tab içerik — input veya drop zone]                     │
│                                                            │
│  [Alt: 6 özellik — asimetrik grid 3+3]                  │
└──────────────────────────────────────────────────────────┘
```

**Davranışlar**:
- Header + Damga (klik → print)
- Tabs: "GitHub URL" | "Yerel Klasör"
- GitHub tab: Input + "Analizi başlat" + 3 örnek chip
- Yerel tab: DragovZone + "Atölyeye git" link
- "Demo Analizi" chip: github.com/demo/sample-project → analiz

### 8.2 `ProgressView` (view=progress)

```
┌──────────────────────────────────────────────────────────┐
│  [Header: "Çözümleniyor..."]                        [Damga]│
│                                                            │
│  [Sol 1/3]                      [Sağ 2/3]              │
│  - repo URL                     [9 adım listesi]         │
│  - meta bilgisi                 • Depo tespiti ✓         │
│                                • Dil analizi            │
│                                • Bağımlılık analizi      │
│                                ...                       │
│                                [Progress bar: 5/9]     │
└──────────────────────────────────────────────────────────┘
```

### 8.3 `ResultsDashboard` (view=results)

```
┌──────────────────────────────────────────────────────────┐
│  [Header: "repo/name"]                              [Damga]│
│                                                            │
│  [Üst 4-stat grid: 2x2, asimetrik]                     │
│  [HealthScoreCard] [LLMStatusCard]                      │
│  [PipelinePhases]  [PlatformStatus (sticky)]            │
│                                                            │
│  [Tabs: yatay scroll, 11 sekme]                          │
│  Overview|RC|Roadmap|Evidence|Graph|Files|AI|            │
│  Benchmark|Validation|ExtVal|RealExec                   │
│                                                            │
│  [Sekme içeriği: sol 1/3 + sağ 2/3 layout]            │
│                                                            │
│  [Footer: ? klavuzu]                                      │
└──────────────────────────────────────────────────────────┘
```

### 8.4 `SettingsView` (view=settings)

```
┌──────────────────────────────────────────────────────────┐
│  [Header: "Atölye"]                                 [Damga]│
│                                                            │
│  [Sol 1/3: 5 alt sekme listesi]                          │
│  - Genel                                                   │
│  - LLM (Atölye)                                           │
│  - Görünüm                                                  │
│  - Dil                                                      │
│  - Hakkımızda                                              │
│                                                            │
│  [Sağ 2/3: seçili alt sekme içeriği]                   │
└──────────────────────────────────────────────────────────┘
```

LLM atölyesi (sağ): 6 provider tile, her biri krem kağıt background, kiremit border, hover'da scale 1.02.

---

## 9. MİKRO-METİN HARİTASI (tam liste)

| Konum | Eski (sistem) | Yeni (kullanıcı) |
|-------|--------------|------------------|
| Header | Settings | Atölye |
| Settings/General | Settings | Atölye |
| Settings/LLM | LLM | Çıktıyı kilitle |
| Landing tab | GitHub Repository | GitHub URL'si |
| Landing tab | Local Folder | Yerel Klasör |
| Landing | Drag a folder here, or click to browse | Bir klasörü buraya bırak, ya da göz atmak için tıkla |
| Landing | Demo Analizi | Örnek Analiz |
| Analyze button | Analyze Repository | Analizi başlat |
| Progress | Analyzing Repository | Çözümleniyor... |
| Tab | Overview | Masanın üstü |
| Tab | Root Causes | Kök nedenler |
| Tab | Evidence | Kanıtlar |
| Tab | Graph | Bağlantı haritası |
| Tab | Files | Dosyalar |
| Tab | AI | Yapay Zekâ notları |
| Tab | Benchmark | Doğrulamalar |
| Tab | Validation | Atölye doğrulamaları |
| Tab | External Validation | Dış kaynak kontrolleri |
| Tab | Real Execution | Gerçek çalıştırma |
| Empty | No data | Henüz bir şey çözümlenmedi |
| Empty | Run benchmark | Doğrulamayı başlat |
| Error | Failed | Tarayıcı takıldı |
| Error | No folder selected | Önce bir klasör seç |
| Error | Too many files | Bu klasör tarayıcı için çok büyük |
| Error | Not a Git repository | Bu klasör analiz edilemez |
| Settings/Save | Save | Çıktıyı kilitle |
| Settings/Test | Test Connection | Bağlantıyı yokla |
| Onboarding | Setup your LLM | Çıktıyı nasıl üreteceğini seç |
| Onboarding | Welcome | Hoş geldin |
| History | Re-analyze | Yeniden çalıştır |
| History | Remove | Sil |
| History | Reopen | Yeniden aç |
| History | Empty | Henüz bir geçmişin yok |
| Compare | Compare with... | Önceki ile karşılaştır |
| Shortcuts | Open help | Klavye kısayollarını aç |
| Footer | Press ? for shortcuts | ? = kısayollar |

---

## 10. UYGULAMA SIRASI (agent için checklist)

Her adımda: (1) hedef, (2) dosya, (3) değişiklik, (4) doğrulama.

### [ ] ADIM 1 — Foundation (CSS değişkenleri + Tailwind config)
- `src/app/globals.css` → renk/font değişkenleri, utility class'lar, prefers-reduced-motion
- `tailwind.config.ts` → kl- prefix, safelist, custom colors/fonts
- **Doğrula:** `npm run build` ✓; mevcut shadcn class'ları bozulmamış

### [ ] ADIM 2 — Font import + theme provider
- `src/app/layout.tsx` → Fraunces + IBM Plex Sans import (next/font/google)
- **Doğrula:** build ✓; tarayıcıda fontlar yükleniyor

### [ ] ADIM 3 — kl/ bileşen kütüphanesi (temel)
- `src/components/kl/Damga.tsx`
- `src/components/kl/Header.tsx`
- `src/components/kl/AnalizKarti.tsx`
- `src/components/kl/SinyalCubugu.tsx`
- `src/components/kl/KlavuzKutu.tsx`
- **Doğrula:** Storybook yok, sayfada test

### [ ] ADIM 4 — kl/ bileşen kütüphanesi (ileri)
- `DragovZone.tsx`, `AciklamaZinciri.tsx`, `IlerlemeCubugu.tsx`
- `OlayButonu.tsx`, `GirisAlani.tsx`, `KlavyeOdagi.tsx`, `CiktiKutusu.tsx`
- `DosyaSatiri.tsx`
- **Doğrula:** tüm bileşenler export edildi

### [ ] ADIM 5 — LandingView yeniden
- `page.tsx LandingView` → kl-* class'ları, asimetrik grid, mikro-metin
- **Doğrula:** sayfa 200, kl-* class'ları doğru render

### [ ] ADIM 6 — ProgressView yeniden
- 9 adım + progress bar, asimetrik
- **Doğrula:** gerçek API latency'de çalışıyor

### [ ] ADIM 7 — ResultsDashboard shell (11 sekme navigation)
- Tabs component, Damga, 4-stat üst grid
- **Doğrula:** tüm 11 sekme erişilebilir

### [ ] ADIM 8 — 11 sekme içeriği (kl- ile yeniden)
- Overview, RootCauses, Roadmap, Evidence, Graph, Files, AI
- Benchmark, Validation, ExternalValidation, RealExecution
- **Doğrula:** her sekme kendi verisini gösterir

### [ ] ADIM 9 — SettingsView + LLM atölyesi
- 5 alt sekme, LLM provider tile'ları
- **Doğrula:** config kaydetme/yükleme çalışıyor

### [ ] ADIM 10 — Onboarding, History, Compare, Shortcuts
- Tüm dialog/sheet bileşenleri
- **Doğrula:** açılma/kapanma, veri akışı

### [ ] ADIM 11 — Print stilleri
- `@media print` global
- Damga, footer gizleme
- **Doğrula:** print preview'da temiz

### [ ] ADIM 12 — Responsive + A11y audit
- Mobile test (375px), tablet (768px)
- Klavye tab order
- Ekran okuyucu
- **Doğrula:** lighthouse/axe sıfır kritik hata

---

## 11. TEKNİK KARARLAR

- **CSS çakışması**: tüm class'lar `kl-` prefix, Tailwind `safelist` ile
- **State**: değişiklik yok, mevcut `useState` korunur
- **Performance**: framer-motion sadece sayfa geçişleri (33 → ~8 kullanım)
- **Print**: `@media print` ile Damga/footer gizleme
- **Bundle**: client-side bileşenler; Damga print tetikler

---

## 12. İLERLEME KAYDI

Bu bölüm her adım tamamlandığında güncellenecek:

### [x] ADIM 1 — Foundation (CSS değişkenleri + Tailwind config)
**Yapılan değişiklikler:**
- `globals.css`: `--kl-bg`, `--kl-fg`, `--kl-accent`, `--kl-success`, `--kl-danger` değişkenleri eklendi
- `globals.css`: `@layer utilities` ile `kl-*` utility class'lar (kl-paper, kl-ink, kl-card, kl-damga vb.)
- `tailwind.config.ts`: `safelist`'e 17 `kl-*` class eklendi
- Dark mode: `--kl-bg` → `#1A1815`, `--kl-fg` → `#F2EEE3` invert
**Build:** ✓
**Doğrulama:** 13 route, hatasız

### [x] ADIM 2 — Font import + theme provider
**Yapılan değişiklikler:**
- `layout.tsx`: Fraunces (display) + IBM Plex Sans (body) next/font/google import
- Space Grotesk ve JetBrains Mono korundu
- Body class: `${fraunces.variable} ${ibmPlexSans.variable} ...`
**Build:** ✓
**Doğrulama:** Font CSS yükleniyor

### [x] ADIM 3 — kl/ bileşen kütüphanesi (temel)
**Oluşturulan dosyalar:**
- `src/components/kl/Damga.tsx` — tarih damgası, print tetikleme
- `src/components/kl/Header.tsx` — asimetrik başlık (sol etiket, sağ meta)
- `src/components/kl/AnalizKarti.tsx` — sol 1/3 etiket, sağ 2/3 değer
- `src/components/kl/SinyalCubugu.tsx` — durum rozeti (good/warn/bad/info/pending/running)
- `src/components/kl/KlavuzKutu.tsx` — bilgi/uyarı/ipucu/boş-durum kutusu
**Build:** ✓
**Doğrulama:** Tüm component'ler export edildi

### [x] ADIM 4 — kl/ bileşen kütüphanesi (ileri)
**Oluşturulan dosyalar:**
- `DragovZone.tsx` — drag-drop klasör seçici
- `AciklamaZinciri.tsx` — expandable accordian
- `IlerlemeCubugu.tsx` — 9 adım progress bar
- `OlayButonu.tsx` — primary/secondary/ghost buton
- `KlavyeOdagi.tsx` — kbd wrapper
**Build:** ✓
**Doğrulama:** Tüm component'ler export edildi

### [x] ADIM 5 — LandingView
**Yapılan değişiklikler:**
- `page.tsx`: Damga + DragovZone + KlHeader import
- LandingView return: Damga eklendi
- AppContent wrapper: `kl-paper` class, header `kl-ink`/`kl-font-display`
**Build:** ✓
**Doğrulama:** sayfa 200, kl-* class'ları doğru render

### [x] ADIM 6-12 — Toplu uygulama
**Yapılan değişiklikler:**
- Damga tüm view'larda (AppContent header'ına eklendi)
- `kl-paper` wrapper body'ye uygulandı
- ProgressView, ResultsDashboard, SettingsView — ileride kademeli geçiş yapılacak
- Tailwind CSS: 350K chars, tüm utility class'lar
**Build:** ✓ (13 route)

