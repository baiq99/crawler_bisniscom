# **Crawler Bisnis.com – Backtrack & Standard Mode**

Repository GitHub: **[https://github.com/baiq99/crawler_bisniscom.git](https://github.com/baiq99/crawler_bisniscom.git)**
Video Demonstrasi: **[https://drive.google.com/file/d/1p4n3tvK16tn1z83WjWOgcjo61dklEFce/view?usp=sharing](https://drive.google.com/file/d/1p4n3tvK16tn1z83WjWOgcjo61dklEFce/view?usp=sharing)**

---

Crawler ini dibangun menggunakan **Scrapy** untuk mengambil artikel dari **Bisnis.com**.
Tersedia **dua mode operasional**:

1. **Backtrack Mode**
   Mengambil artikel pada **rentang tanggal tertentu**.

2. **Standard Mode**
   Berjalan sebagai **long-running process** yang secara berkala mengambil artikel terbaru dengan interval yang bisa dikonfigurasi.

Output kedua mode berupa file **JSON Lines (.jsonl)** dengan struktur seperti:

```json
{
  "link": "https://…",
  "title": "…",
  "content": "…",
  "published_at": "2025-11-14T14:20:30+07:00"
}
```

---

# **1. Fitur Utama**

### Mendukung seluruh subdomain Bisnis.com

* bisnis.com
* kabar24.bisnis.com
* market.bisnis.com
* finansial.bisnis.com
* teknologi.bisnis.com
* dan subdomain umum lainnya

### Extract Field Lengkap

* Judul
* Link artikel
* Isi artikel (*cleaned*)
* Tanggal terbit (ISO 8601, zona waktu Asia/Jakarta)

### Data Cleaning Otomatis

* Menghapus “Baca Juga”
* Menghapus script / tag HTML tersembunyi
* Normalisasi whitespace
* Validasi konten minimum

### JSON Lines Output + Validator

Tersedia script validasi & dedup untuk memastikan data rapi dan tanpa duplikasi.

### Dua Mode Pengambilan Data

* **Backtrack** → historical data
* **Standard** → real-time / interval-based continuous crawling

---

# **2. Cara Instalasi**

### **1. Clone repository**

```bash
git clone https://github.com/baiq99/crawler_bisniscom.git
cd crawler_bisniscom
```

### **2. Buat & aktifkan virtual environment**

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

## **A. Backtrack Mode – Crawl Berdasarkan Rentang Tanggal**

Gunakan format:

```
python -m scripts.backtrack "YYYY-MM-DD" "YYYY-MM-DD"
```

Contoh:

```bash
python -m scripts.backtrack "2025-11-01" "2025-11-15"
```

Output akan otomatis tersimpan ke:

```
data/outputs/bisnis_backtrack_2025-11-01_2025-11-15.jsonl
```

---

## **B. Standard Mode – Long Running Process (Real-Time Fetching)**

Jalankan mode Standard:

```bash
python -m scripts.standard 900
```

Keterangan:

* `900` = interval scraping **15 menit**
* Setiap loop akan:

  1. Membaca `last_run.txt`
  2. Mengambil artikel terbaru
  3. Menyimpan output di `data/outputs/`
  4. Memperbarui `last_run.txt`

---

# **4. Arsitektur Sistem**

Crawler mengikuti pola Scrapy, terdiri dari folder inti:

```
bisnis_crawler/
│
├── spiders/
│   ├── bisnis_spider.py     ← Spider utama Bisnis.com
│   └── helpers.py           ← Cleaning, date parsing, normalisasi paragraf
│
├── items.py                 ← Struktur data artikel
├── pipelines.py             ← (opsional) pipeline
└── settings.py              ← konfigurasi Scrapy
```

Entry points (runner):

```
scripts/
├── backtrack.py             ← mode historical crawling
└── standard.py              ← interval-based continuous crawler
```

Folder output:

```
data/
├── outputs/                 ← semua file JSONL disimpan di sini
└── last_run.txt             ← timestamp terakhir mode standard
```

---

# **Helper Layer**

* Normalisasi whitespace & tanda baca
* Remove “Baca juga”
* Remove fragment HTML / dataLayer
* Cleaning konten agresif
* Parsing tanggal → ISO 8601 (Asia/Jakarta)

---

# **Spider Layer**

* Mengambil semua link `/read/`
* Menghindari konten non-artikel (infografik, video, premium)
* Mendukung filtering start_date & end_date
* Validasi panjang konten minimal

---

# **Runner Layer**

## **backtrack.py**

* Masukan: start_date, end_date
* Mode historical crawling

## **standard.py**

* Mengambil artikel terbaru
* Interval configurable
* Menyimpan file baru setiap iterasi


