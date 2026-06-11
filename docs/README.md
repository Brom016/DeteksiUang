# Sistem Verifikasi Uang Kertas Rupiah TE 2022
### Berbasis Konversi Ruang Warna HSV dan Geometri Citra  
### Sebagai Alat Bantu Tunanetra

---

## Struktur Proyek

```
DeteksiUang/
├── src/                 # Kode sistem utama
│   ├── config.py        Constants, database nominal, parameter tunable
│   ├── preprocessor.py  Grayscale, Blur, Canny, findContours
│   ├── rectifier.py     minAreaRect, order_points, warpPerspective
│   ├── feature_extractor.py  Aspek rasio & fraksi hue HSV
│   ├── classifier.py    Klasifikasi + confidence scoring
│   ├── tts_engine.py    Text-to-Speech (pyttsx3 / gTTS / console)
│   ├── pipeline.py      Orkestrasi pipeline lengkap
│   ├── main.py          Entry point (kamera / gambar / kalibrasi)
│   └── test_pipeline.py Pengujian otomatis gambar sintetis
├── images/              # Contoh gambar uang untuk mode statis
├── assets/              # Gambar & media
│   ├── flowchart.drawio.png
│   └── audio_cache/     # Cache suara TTS
├── docs/                # Dokumentasi
│   ├── README.md
│   ├── catatan.md
│   ├── Konteks.md
│   ├── flowchart.md
│   └── userflow.md
└── requirements.txt
```

---

## Instalasi

```bash
pip install -r requirements.txt
```

Dependensi:
- `opencv-python`  - Seluruh proses PCD
- `numpy`          - Komputasi matriks
- `pyttsx3`        - TTS offline (Windows/Linux/macOS)
- `gTTS + pygame`  - TTS online bahasa Indonesia (fallback)

---

## Cara Menjalankan

### Mode Kamera (penggunaan utama)
```bash
python src/main.py
```
- Arahkan kamera ke uang kertas di atas permukaan polos
- Deteksi berjalan otomatis (tanpa tombol)
- Tekan **Q** untuk keluar

### Mode Debug (tampilkan overlay metrik)
```bash
python src/main.py --debug
```

### Mode Gambar Statis
```bash
python src/main.py --image images/foto_uang.jpg
python src/main.py --image images/foto_uang.jpg --debug
```

### Mode Kalibrasi HSV
```bash
python src/main.py --calibrate
```
Gunakan slider untuk menemukan rentang Hue yang tepat untuk setiap nominal
di bawah kondisi pencahayaan kamera Anda. Tekan **S** untuk menyimpan nilai,
lalu perbarui `hue_ranges` di `src/config.py`.

### Pengujian Otomatis
```bash
python src/test_pipeline.py
```
Menjalankan seluruh pipeline terhadap gambar sintetis. Tidak memerlukan
kamera fisik maupun uang asli.

---

## Cara Kerja (Pipeline PCD)

```
[Input Foto Uang]
    ↓ Grayscale + Gaussian Blur
    ↓ Canny Edge Detection
    ↓ findContours → pilih kontur terbesar yang berbentuk persegi
    ↓ minAreaRect + boxPoints → 4 titik sudut
    ↓ warpPerspective → gambar uang lurus & terpotong
    ↓ Hitung Aspek Rasio (panjang / lebar)
    ↓ Hitung fraksi piksel HSV sesuai warna nominal target
    ↓ Cross-validasi: Geometri + Warna → Verdict
    ↓ [Output TTS]
```

### Database Nominal BI TE 2022

| Nominal      | Panjang | Aspek Rasio | Warna Dominan |
|:------------|:-------:|:-----------:|:--------------|
| Rp 100.000  | 151 mm  | 2.3231      | Merah         |
| Rp  50.000  | 149 mm  | 2.2923      | Biru          |
| Rp  20.000  | 147 mm  | 2.2615      | Hijau         |
| Rp  10.000  | 145 mm  | 2.2308      | Ungu          |
| Rp   5.000  | 143 mm  | 2.2000      | Coklat        |
| Rp   2.000  | 141 mm  | 2.1692      | Abu-abu Hijau |
| Rp   1.000  | 139 mm  | 2.1385      | Perak/Abu-abu |

Semua nominal memiliki lebar seragam **65 mm**. Penggunaan aspek rasio
(bukan panjang absolut piksel) membuat sistem tidak terpengaruh jarak kamera.

---

## Kalibrasi HSV

**Langkah yang diperlukan sebelum deployment:**

1. Jalankan `python main.py --calibrate`
2. Letakkan masing-masing nominal di depan kamera
3. Geser slider H Min / H Max hingga hanya warna dominan uang yang terlihat di mask
4. Tekan **S** untuk mencetak nilai ke konsol
5. Perbarui `hue_ranges` di `src/config.py` untuk nominal tersebut

Nilai default yang tersedia adalah **estimasi**. Akurasi warna sangat bergantung
pada kamera dan kondisi pencahayaan ruangan Anda.

---

## Toleransi & Parameter Tunable (src/config.py)

| Parameter                 | Default | Keterangan                                        |
|:--------------------------|:-------:|:--------------------------------------------------|
| `ASPECT_RATIO_TOLERANCE`  | 0.013   | ±0.013 dari AR target. Selisih antar nominal 0.031 |
| `MIN_HUE_PIXEL_FRACTION`  | 0.10    | Min 10% piksel harus cocok dengan rentang Hue     |
| `REQUIRE_BOTH_FEATURES`   | True    | False = geometri saja yang menentukan             |
| `CANNY_THRESHOLD_LOW`     | 30      | Kurangi jika tepi uang tidak terdeteksi           |
| `CANNY_THRESHOLD_HIGH`    | 120     | Naikkan jika background memunculkan banyak noise  |
| `MIN_CONTOUR_AREA_RATIO`  | 0.08    | Uang harus mengisi ≥8% frame                      |

---

## Keterbatasan Sistem (penting untuk sidang)

1. **"Asli" bukan autentikasi penuh.**  
   Sistem hanya memverifikasi bahwa dimensi fisik dan warna dominan sesuai standar
   BI. Sistem tidak dapat mendeteksi fitur keamanan UV, benang pengaman, tanda air,
   atau microprinting. Uang palsu berkualitas tinggi dengan ukuran dan warna yang
   benar dapat lolos verifikasi ini.

2. **Selisih aspek rasio sangat kecil.**  
   Perbedaan antar nominal hanya ≈0.031. Foto miring, kertas lecek, atau kontur
   yang tidak terdeteksi sempurna dapat menyebabkan mismatch. Background polos
   dan pencahayaan merata sangat direkomendasikan.

3. **Rp 1.000 dan Rp 2.000 lebih sulit diklasifikasi berdasarkan warna.**  
   Keduanya memiliki saturasi rendah (perak/abu-abu). Akurasi warna untuk
   kedua nominal ini lebih bergantung pada aspek rasio.

4. **Harus dikalibrasi per kamera.**  
   Nilai HSV berbeda antar kamera dan kondisi pencahayaan. Kalibrasi ulang
   diperlukan setiap kali lingkungan berubah secara signifikan.

5. **Background harus kontras dan polos.**  
   Background bermotif atau berwarna-warni akan menghasilkan false contour
   yang mengganggu deteksi.

---

## Output TTS

| Kondisi                     | Output Suara                              |
|:---------------------------|:------------------------------------------|
| Terdeteksi, valid           | "Lima Puluh Ribu Rupiah, Asli"           |
| Terdeteksi, warna mismatch  | "Seratus Ribu Rupiah, Mencurigakan atau Palsu" |
| Tidak ada kontur            | "Uang Tidak Terlihat, Dekatkan Kamera"   |
| Aspek rasio tidak cocok     | "Uang Tidak Dikenali atau Palsu"         |