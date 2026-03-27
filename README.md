# 🏙️ LandIntel — Türkiye Gayrimenkul İstihbarat Radarı

> Resmi Gazete'yi her gün otomatik tarayarak kamulaştırma, özelleştirme ve imar kararlarını yakalayan, GPT-4 ile analiz eden ve portföy eşleşmesi halinde uyarı gönderen AI destekli bir gayrimenkul istihbarat sistemi.

---

## 🎯 Ne Yapar?

Türkiye'de her gün Resmi Gazete'de yüzlerce hukuki karar yayınlanır:
- Arazi **kamulaştırmaları**
- Hazine taşınmazı **özelleştirmeleri**
- **İmar** değişiklikleri
- Taşınmaz **ihale** kararları

Bu kararları takip etmek büyük fırsat/risk sinyalleridir ama elle takip etmek imkânsızdır.

**LandIntel** bu süreci tamamen otomatize eder:

```
Resmi Gazete → PDF İndir → LlamaParse → Gemini (Map) → GPT-4o (Reduce) → Intelligence Report → Portföy Eşleşmesi → E-mail/WhatsApp Uyarısı
```

---

## 🏗️ Mimari

```
LandIntel/
├── hunter/          # Resmi Gazete scraper + PDF downloader
├── parser/          # LlamaParse PDF → Markdown/JSON dönüştürücü
├── brain/           # Map-Reduce AI analiz motoru
│   ├── map_analyzer.py      # Gemini Flash (chunk analizi)
│   ├── reduce_synthesizer.py # GPT-4o-mini (final rapor)
│   └── prompts.py           # AI prompt şablonları
├── memory/          # ChromaDB vektör hafızası + portföy yönetimi
├── radar/           # Orchestrator, scheduler, alert engine, dashboard
├── config/          # Merkezi ayarlar (pydantic-settings)
├── templates/       # E-mail HTML şablonları
├── data/            # Runtime veri klasörleri (gitignore'da)
│   ├── raw_pdfs/
│   ├── parsed_markdown/
│   ├── parsed_json/
│   ├── intelligence_reports/
│   └── chroma_db/
└── main.py          # Tek giriş noktası (CLI)
```

---

## ⚙️ Nasıl Çalışır?

### 1️⃣ Hunter — Resmi Gazete Tarayıcı

`hunter/gazette_hunter.py`

- `https://www.resmigazete.gov.tr` sitesini `httpx` + `BeautifulSoup` ile tarar
- PDF linklerini bulur
- Başlıkları keyword listesiyle filtreler (`taşınmaz`, `kamulaştırma`, `ihale`, `özelleştirme`...)
- Eşleşen PDF'leri `data/raw_pdfs/` klasörüne indirir
- İdempotent: aynı PDF ikinci kez indirilmez (`data/download_queue.json`)

### 2️⃣ Parser — PDF → Yapılandırılmış Veri

`parser/pdf_parser.py`

- LlamaParse API ile Türkçe PDF'leri OCR + yapısal metin olarak çözer
- Tablolar (taşınmaz listeleri, parsel numaraları) korunur
- `data/parsed_markdown/` → ham metin
- `data/parsed_json/` → çunk'lanmış, metadata eklenmiş JSON

### 3️⃣ Brain — Map-Reduce AI Analiz

`brain/intelligence_engine.py`

**MAP Aşaması (Gemini 2.0 Flash):**
Her chunk ayrı ayrı analiz edilir:
- İşlem türü (kamulaştırma / özelleştirme / ihale)
- Etkilenen ilçe/mahalle
- Parsel numaraları
- Parasal değerler
- Fırsat/risk skoru

**REDUCE Aşaması (GPT-4o-mini):**
Tüm chunk analizleri birleştirilir, tek bir yapılandırılmış `Intelligence Report` üretilir → `data/intelligence_reports/*.json`

### 4️⃣ Memory — Vektör Hafızası

`memory/vector_store.py`

- ChromaDB kullanır
- Intelligence raporlar ve portföy kayıtları `text-embedding-3-small` ile vektörleştirilir
- Anlamsal benzerlik araması ile "bu karar müşterimle ilgili mi?" sorusu cevaplanır

### 5️⃣ Radar — Portföy Eşleşmesi + Uyarı

`radar/alert_engine.py`

- Yeni rapor, B2B portföyündeki kayıtlarla karşılaştırılır (cosine similarity > 0.75)
- Eşleşme bulunursa e-mail (SMTP) ve/veya WhatsApp (Twilio) uyarısı gönderilir

---

## 🚀 Kurulum

### Gereksinimler
- Python 3.11+
- API Anahtarları: LlamaParse, OpenAI, Google AI Studio

### 1. Sanal ortam oluştur
```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
```

### 2. `.env` dosyasını oluştur
```bash
cp .env.example .env
```

`.env` dosyasını düzenle:
```env
LLAMA_CLOUD_API_KEY=llx-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
MAP_MODEL=models/gemini-2.0-flash
REDUCE_MODEL=gpt-4o-mini
```

---

## 🖥️ Kullanım

### Tek seferlik çalıştır
```bash
python main.py run-now --days-back 1
```

### Sadece Hunter'ı test et (API maliyeti yok)
```bash
python -m hunter.gazette_hunter --days-back 3
```

### Durumu göster
```bash
python main.py dashboard
```

### Portföy yükle
```bash
python main.py add-portfolio -i data/portfolio_seed.json
```

### 7/24 Otomatik (her sabah 07:00 İstanbul)
```bash
python main.py start
```

---

## 📁 Veri Yapısı

### Intelligence Report (`data/intelligence_reports/*.json`)
```json
{
  "gazette_date": "2026-03-27",
  "document_type": "Kamulaştırma Kararı",
  "summary_tr": "Kuşadası-Söke içmesuyu projesi kapsamında...",
  "opportunities": [...],
  "risks": [...],
  "key_locations": ["Aydın", "Kuşadası"],
  "confidence_score": 0.92
}
```

### Portföy Kaydı (`data/portfolio_seed.json`)
```json
[
  {
    "client_name": "Örnek A.Ş.",
    "location": "İzmir, Kuşadası",
    "property_type": "Arsa",
    "notes": "Kıyıya yakın, kamulaştırma riski takip ediliyor"
  }
]
```

---

## 🔑 Gerekli API Anahtarları

| Servis | Kullanım | Nereden Alınır |
|--------|----------|----------------|
| **LlamaParse** | PDF → Metin | [cloud.llamaindex.ai](https://cloud.llamaindex.ai) |
| **OpenAI** | Reduce + Embedding | [platform.openai.com](https://platform.openai.com) |
| **Google AI Studio** | Map (Gemini) | [aistudio.google.com](https://aistudio.google.com) |
| **Twilio** *(opsiyonel)* | WhatsApp uyarısı | [twilio.com](https://twilio.com) |
| **SMTP** *(opsiyonel)* | E-mail uyarısı | Gmail App Password vb. |

---

## 🗓️ Scheduler Ayarları (`.env`)

```env
SCHEDULE_HOUR=7              # Sabah 07:00'de çalış
SCHEDULE_TIMEZONE=Europe/Istanbul
```

---

## 📊 Keyword Listesi

Varsayılan olarak şu anahtar kelimeler aranır:

```
imar, kamulaştırma, ihale, tapu, taşınmaz, özelleştirme,
istimlak, kentsel dönüşüm, yapı denetim, ruhsat, parsel,
kadastro, gayrimenkul, arazi, mera, orman, kıyı kanunu
```

`.env` dosyasından özelleştirilebilir:
```env
KEYWORDS='["imar","kamulaştırma","taşınmaz"]'
```

---

## ⚠️ Önemli Notlar

- `.env` dosyası **asla** Git'e gönderilmemelidir (`.gitignore`'da belirtilmiştir)
- Gemini ücretsiz katmanı günlük ~100 istek ile sınırlıdır
- Production için bir VPS'de `python main.py start` + `tmux` ya da `systemd` önerilir

---

## 📄 Lisans

MIT
