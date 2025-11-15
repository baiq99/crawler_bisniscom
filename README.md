Crawler ini dibangun menggunakan **Scrapy** untuk mengambil artikel dari **Bisnis.com**.
Proyek menyediakan **dua mode operasional**:

1. **Backtrack Mode**
   Mengambil artikel dalam rentang tanggal tertentu (misal 1–15 November 2025).

2. **Standard Mode**
   Long-running process yang secara berkala menarik artikel terbaru dengan interval waktu terkonfigurasi.

Output masing-masing mode berupa file **JSON Lines (.jsonl)** berisi artikel dengan struktur:

```json
{
  "link": "https://…",
  "title": "…",
  "content": "…",
  "published_at": "2025-11-14T14:20:30+07:00"
}
```


## **1. Fitur Utama**

### Scraper untuk seluruh domain Bisnis.com

* bisnis.com
* kabar24.bisnis.com
* market.bisnis.com
* teknologi.bisnis.com
* finansial.bisnis.com
* dan subdomain utama lainnya

### Extract Field:

* Judul
* Tautan
* Isi artikel (dibersihkan dari script/style/“baca juga”/noise)
* Tanggal terbit (dibersihkan & dinormalisasi ke Asia/Jakarta ISO-8601)

### Output JSONL dengan data yang benar-benar valid

Tersedia script validasi & dedup.

### Interval-based continuous crawling

Mode *standard* berjalan terus-menerus dan mengambil only-new-articles.

### Backtrack historical crawling

Mode *backtrack* mengambil berita pada rentang tanggal besar sekaligus.

---

## **2. Cara Instalasi**

### **1. Clone & masuk folder**

```bash
git clone <repo_url>
cd nolimit-crawler
```

### **2. Aktifkan virtual environment**

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
```

### **3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

# **3. Cara Menjalankan**

## **A. Backtrack Mode (Crawl berdasarkan rentang tanggal)**

Jalankan:

```bash
python -m scripts.backtrack --start 2025-11-01 --end 2025-11-15 --output data/outputs/bisnis_backtrack.jsonl --rate 1.0 --max-pages 400
```

Hasil akan disimpan di:

```
data/outputs/bisnis_backtrack_YYYY-MM-DD_YYYY-MM-DD.jsonl
```

---

## **B. Standard Mode (Long Running Process)**

Mode ini berjalan selamanya dan mengambil artikel baru berdasarkan waktu terakhir.

### Jalankan:

```bash
python -m scripts.standard 900
```

`900` berarti interval 15 menit.
Output disimpan otomatis di `data/outputs/`.

File `data/last_run.txt` akan diperbarui setiap proses selesai.

---

# **4. Arsitektur Sistem**

Crawler mengikuti arsitektur Scrapy standar namun ditambah modul pendukung:

```
bisnis_crawler/
│
├── spiders/
│   ├── bisnis_spider.py     ← Spider utama Bisnis.com
│   └── helpers.py           ← Cleaning, date parser, paragraph normalizer
│
├── items.py                 ← Struktur data artikel
├── pipelines.py             ← (opsional) pipeline data
└── settings.py              ← konfigurasi Scrapy
```

Supporting scripts:

```
scripts/
├── backtrack.py             ← mode crawling historical
└── standard.py              ← long-running real-time crawler
```

Data management:

```
data/
├── outputs/                 ← semua output JSONL
└── last_run.txt             ← penanda waktu terakhir crawling
```

### **Helper Layer**

Bagian yang menguatkan kualitas data:

* Normalisasi whitespace & tanda baca
* Menghapus “Baca juga”, fragment HTML, dataLayer
* Cleaning agresif pada konten
* Parser tanggal → ISO 8601 dengan Asia/Jakarta

### **Spider Layer**

* Navigasi link artikel `/read/`
* Filter konten non-artikel (video, infografik, premium)
* Support start_date & end_date untuk mode backtrack & standard

### **Runner Layer (Scripts)**

* `backtrack.py` → mengambil artikel historis dalam range tanggal
* `standard.py` → loop otomatis interval-based, update last_run

---
