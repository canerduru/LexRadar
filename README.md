# LexRadar (Legal Intelligence Radar) ⚖️

*LexRadar*, resmi makamların yayımladığı kararları, mevzuat değişikliklerini ve ihaleleri otomatik olarak takip eden, yapay zeka destekli kurumsal düzeyde bir **Hukuki İstihbarat Radarıdır**.

*LexRadar is an AI-powered, enterprise-grade **Legal Intelligence Radar** that automatically tracks decisions, regulatory changes, and public tenders published by official authorities.*

---

## 🇹🇷 Türkçe (Turkish)

### 📌 Proje Hakkında
LexRadar, şirketlerin ve hukuk bürolarının, kendi sektörlerini ve "İzleme Listelerindeki" (Watchlist) müvekkillerini doğrudan ilgilendiren yasal gelişmeleri anında yakalamasını sağlar. Her gün **T.C. Resmi Gazete**'yi tarayıp, PDF belgelerini indirir ve **LlamaParse**, **Google Gemini**, ve **OpenAI GPT-4o-mini** altyapılarıyla hukuki bir bağlamda analiz ederek karar, kanun, ihale ve risk analizlerini özetleyip WhatsApp ve E-posta yoluyla otomatik bildirimler gönderir.

### 🏗️ Nasıl Çalışır?
Sistem 5 ana aşamadan (Pipeline) oluşur:

1. **Hunter (Avcı):** Seçili yasal kelime grubuna göre (`dava`, `rekabet`, `kvkk` vb.) o günkü Resmi Gazete'yi tarar. İlgili belgelerin PDF hallerini bulup indirir.
2. **Parser (Çözümleyici):** `LlamaParse` yardımı ile karmaşık yapılı hukuki PDF belgelerini kusursuzca metne (Markdown/JSON) çevirir.
3. **Brain (Yapay Zeka - Map/Reduce):**
    - **Map:** Google Gemini her parçayı okuyarak "Türk Hukuk İstihbarat Analisti" edasıyla bilgileri ayrıştırır, sektörleri ve riskleri (`LOW`, `MED`, `HIGH`) tespit eder.
    - **Reduce:** OpenAI GPT-4o-mini devreye girip bir "Başhukuk Müşaviri" perspektifinden tüm bulguları tek bir `FinalReport` json belgesinde birleştirir.
4. **Memory (Hafıza - ChromaDB):** Analiz sonuçları Vektör veritabanına eklenir. `ClientWatchlist` (Müvekkil İzleme Listesi) üzerinden şirketler veya sektörler ile eşleşmeler aranır (Dava numarasından veya şirket unvanından %100 eşleşme gibi ağırlıklandırılmış sistem).
5. **Radar (Bildirim):** Eşleşen önemli hukuki olaylar, **Aciliyet Seviyesi** ve **Önerilen Eylem** planıyla beraber WhatsApp/E-posta şablonlarına oturtulup ilgili sorumlulara gönderilir.

### 🚀 Karşılaştırma Mantığı (Heuristic Matching)
Bağlam eşleştirme sırası şu şekildedir:
- Öncelik 1: Tam dava numarası eşleşmesi (`score: 1.0`)
- Öncelik 2: Müvekkil/Şirket unvanı eşleşmesi (`score: 0.95`)
- Öncelik 3: Hukuki alan ve sektörün birleşimi (`score: 0.85`)
- Öncelik 4: İzleme listesindeki anahtar kelimelerin anlamsal (vektörel) eşleşmesi.

### ⚙️ Kurulum ve Çalıştırma
```bash
# Sanal ortamı aktif edin
python3.11 -m venv .venv311
source .venv311/bin/activate

# Gereksinimleri yükleyin
pip install -r requirements.txt
```

**.env** dosyasını oluşturun ve API Anahtarlarını girin:
```env
LLAMA_CLOUD_API_KEY="your_key"
GOOGLE_API_KEY="your_key"
OPENAI_API_KEY="your_key"
# (Opsiyonel: Twilio / E-posta SMPT Ayarları)
```

**Sistemi Test Etmek:**
```bash
# Son 2 günü taramak için (Test formatında)
python main.py run-now --days-back 2
```

---

## 🇬🇧 English

### 📌 About the Project
LexRadar enables companies and law firms to instantly capture legal developments that directly affect their sectors and specific clients on their "Watchlists". Scanning the **Turkish Official Gazette** daily, LexRadar downloads PDFs and processes them through an AI pipeline using **LlamaParse**, **Google Gemini**, and **OpenAI GPT-4o-mini**. It curates actionable legal intelligence reports and distributes tailored email/WhatsApp alerts.

### 🏗️ How it Works
The system follows a 5-stage pipeline:

1. **Hunter:** Scans the daily Official Gazette against targeted legal keywords (e.g., `litigation`, `competition`, `kvkk`) and queues relevant PDFs for download.
2. **Parser:** Utilizes `LlamaParse` to transform visually complex court/legal PDF documents into highly accurate machine-readable markdown and JSON data.
3. **Brain (AI Engine - Map/Reduce):**
    - **Map:** Google Gemini acts as an Intelligence Analyst, determining the decision type, affected sectors, key entities, and stratifying legal risks (`LOW`, `MED`, `HIGH`).
    - **Reduce:** OpenAI's GPT-4o-mini acts as Senior Legal Counsel to synthesize all analyzed chunks into an authoritative single JSON intelligence report.
4. **Memory (ChromaDB + Heuristics):** Analyzed documents are embedded into a local Vector DB. The engine filters matches against the `ClientWatchlist` to check for relevant criteria such as case numbers, tracking keywords, and sectors.
5. **Radar (Notification Engine):** Generates robust alerts identifying the `match_type` and `urgency_level`, alongside recommended legal actions, and dispatches them automatically over WhatsApp/Email.

### 🚀 Matching Algorithm
When looking for watchlist matches, the engine scores as follows:
- Priority 1: Exact case reference match (`score: 1.0`)
- Priority 2: Direct Company/Client entity match (`score: 0.95`)
- Priority 3: Combined Legal Area + Sector intersection (`score: 0.85`)
- Priority 4: Semantic similarity on watchlist keywords.

### ⚙️ Installation & Usage
```bash
# Create and activate local environment
python3.11 -m venv .venv311
source .venv311/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a **.env** file modeled on `.env.example` and plug in your keys:
```env
LLAMA_CLOUD_API_KEY="your_key"
GOOGLE_API_KEY="your_key"
OPENAI_API_KEY="your_key"
# (Optional: Twilio / Email SMTP Settings)
```

**Running the System:**
```bash
# Scrape and analyze the last 2 days of the Official Gazette immediately
python main.py run-now --days-back 2
```

---
*Architecture based on the original intelligence pipeline; highly customized for Legal AI Operations.*
