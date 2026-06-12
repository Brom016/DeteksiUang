# Sistem Verifikasi Uang Kertas Rupiah TE 2022
### Deteksi Angka Nominal via Snapshot + Template Matching, Warna HSV, dan Geometri Citra
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
│   ├── number_detector.py    Deteksi angka nominal via template matching
│   ├── classifier.py    Klasifikasi (angka → AR cross-validate → warna) + confidence
│   ├── calibrator.py    Auto-kalibrasi HSV dari deteksi langsung
│   ├── tts_engine.py    Text-to-Speech (pyttsx3 / gTTS / console)
│   ├── pipeline.py      Orkestrasi pipeline lengkap
│   ├── main.py          Entry point (kamera / gambar / kalibrasi)
│   └── test_pipeline.py Pengujian otomatis gambar sintetis
├── images/              # Contoh gambar uang untuk mode statis
├── assets/
│   ├── templates/       # Template angka nominal (real crop dari sampel)
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
- `opencv-python`  - Seluruh proses PCD (termasuk template matching)
- `numpy`          - Komputasi matriks
- `pyttsx3`        - TTS offline (Windows/Linux/macOS)
- `gTTS + pygame`  - TTS online bahasa Indonesia (fallback)

---

## Cara Menjalankan

### Mode Kamera — Snapshot (penggunaan utama)
```bash
python src/main.py
```
- Arahkan kamera ke uang kertas
- Sistem mendeteksi kontur tiap frame (cepat, ~15ms)
- Saat kontur stabil 5 frame → **snapshot** → diproses 1 kali secara teliti
- Hasil diumumkan via TTS, tanpa buffer akumulasi
- Tekan **Q** untuk keluar

### Mode Debug
```bash
python src/main.py --debug
```
Menampilkan overlay metrik (number detection, color score, aspect ratio)
langsung di layar.

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

### Streaming Mode (alternatif)
Set `SNAPSHOT_MODE = False` di `config.py` untuk menggunakan pendekatan
lama: pipeline penuh tiap frame + akumulasi stability buffer.

### Pengujian Otomatis
```bash
python src/test_pipeline.py
```
Menjalankan seluruh pipeline terhadap gambar sintetis.

---

## Cara Kerja

### Snapshot Mode (default)

```
[ Kamera ~30fps ]
  ↓ quick_contour_detect()   (15 ms — hanya Canny + contour)
  ↓
  Kontur stabil ≥ 5 frame?
  ├── Tidak → lanjut preview
  └── Ya → [SNAPSHOT] ambil frame saat itu
            ↓
    1. rectify → warpPerspective (640 px)
    2. Template matching angka
       - 12 scales × 9 sliding ROI positions (detect_number_enhanced)
    3. Cross-validate dengan Aspect Ratio
       - Jika ar_s < 0.1 → false positive → fallback AR + warna
    4. Jika angka cocok & AR setuju:
         Final = num_conf × 0.65 + color_s × 0.35
    5. Jika angka tidak terdeteksi/ditolak:
         Cari nominal dengan AR + warna terbaik
    6. [Output TTS]
```

### Streaming Mode (SNAPSHOT_MODE = False)

```
[ Input Frame ]  →  pipeline penuh  →  stability buffer 3 frame  →  TTS
                    (setiap frame)       (harus identik berturut)
```

---

## Database Nominal BI TE 2022

| Nominal      | Panjang | Aspek Rasio | Step | Warna Dominan | Jumlah Digit |
|:------------|:-------:|:-----------:|:----:|:--------------|:------------:|
| Rp 100.000  | 151 mm  | 2.3231      | —    | Merah         | 6            |
| Rp  50.000  | 146 mm  | 2.2462      | 5 mm | Biru          | 5            |
| Rp  20.000  | 141 mm  | 2.1692      | 5 mm | Hijau         | 5            |
| Rp  10.000  | 136 mm  | 2.0923      | 5 mm | Ungu          | 5            |
| Rp   5.000  | 131 mm  | 2.0154      | 5 mm | Coklat        | 4            |
| Rp   2.000  | 126 mm  | 1.9385      | 5 mm | Abu-abu Hijau | 4            |
| Rp   1.000  | 121 mm  | 1.8615      | 5 mm | Perak/Abu-abu | 4            |

Semua nominal lebar **65 mm**. Step 5 mm menghasilkan ΔAR ≈ 0.077 —
cukup besar untuk dibedakan secara robust oleh sistem.

---

## Deteksi Angka Nominal

### Metode
Snapshot di-rectify (warpPerspective ke 640 px). Sistem memotong
pojok kanan-bawah dan mencocokkan dengan template referensi via
`cv2.matchTemplate(TM_CCOEFF_NORMED)`.

### Snapshot Mode — Enhanced
`detect_number_enhanced()` dipanggil sekali per snapshot:
- **12 skala** (0.55× – 1.55×) untuk toleransi ukuran
- **9 sliding window** (3×3 offset ±2%) — compensasi rectification error
- Early exit jika confidence > 0.92

### Skoring & Cross-Validation
1. **Number detection** (confidence ≥ 0.30) → dicek AR:
   - AR cocok (ar_s ≥ 0.1) → **Primary**: `num_conf × 0.65 + color × 0.35`
   - AR tidak cocok (ar_s < 0.1) → **False positive** → fallback
2. **Fallback** (angka tidak terdeteksi atau ditolak):
   - Iterasi semua nominal, skor = `ar_s × (0.6 + 0.4 × color_s)`
3. **Authenticity** butuh color_s > 0.15 atau number_ok + skor > 0.2

### Template
- Disimpan di `assets/templates/{value}.png`
- Multi-scale matching (coarse-to-fine: 5 coarse + ~2 fine)
- Threshold: 0.30
- Template tersedia untuk Rp 100.000, Rp 50.000, Rp 20.000
- Nominal lain fallback ke AR + warna

---

## Kalibrasi HSV

**Langkah yang diperlukan sebelum deployment:**

1. Jalankan `python main.py --calibrate`
2. Letakkan masing-masing nominal di depan kamera
3. Geser slider H Min / H Max hingga hanya warna dominan uang yang terlihat di mask
4. Tekan **S** untuk mencetak nilai ke konsol
5. Perbarui `hue_ranges` di `src/config.py` untuk nominal tersebut

`AUTO_CALIBRATE` default **False** — dapat diaktifkan setelah hue_ranges
terverifikasi. Auto-kalibrasi menyimpan profil ke `calibration_profile.json`.

---

## Toleransi & Parameter Tunable (src/config.py)

### Detection Mode
| Parameter                  | Default | Keterangan                                      |
|:---------------------------|:-------:|:------------------------------------------------|
| `SNAPSHOT_MODE`            | True    | True = snapshot (cepat + akurat), False = streaming |
| `SNAPSHOT_CONTOUR_STREAK`  | 5       | Frame kontur stabil sebelum snapshot            |
| `SNAPSHOT_COOLDOWN`        | 2.0 s   | Jeda antar snapshot                             |
| `MAX_PREVIEW_FPS`          | 30      | Kecepatan cek kontur (frame rate)               |

### Matching
| Parameter                    | Default | Keterangan                                      |
|:-----------------------------|:-------:|:------------------------------------------------|
| `ASPECT_RATIO_TOLERANCE`     | 0.025   | ±0.025 AR (step antar nominal 0.077)            |
| `MIN_HUE_PIXEL_FRACTION`     | 0.10    | Min 10% piksel cocok hue target                 |
| `HUE_PEAK_MARGIN`            | 8       | Margin ±8 hue untuk dominant hue match          |
| `NUMBER_ROI`                 | (0.50, 0.55, 0.98, 0.95) | Crop pojok kanan-bawah (x1,y1,x2,y2) |
| `TEMPLATE_MATCH_THRESHOLD`   | 0.30    | Min confidence template match                   |
| `NUMBER_WEIGHT`              | 0.65    | Bobot number detection                          |
| `COLOR_WEIGHT`               | 0.35    | Bobot color match                               |

### Pipeline
| Parameter                  | Default | Keterangan                                      |
|:---------------------------|:-------:|:------------------------------------------------|
| `WARP_OUTPUT_WIDTH`        | 640 px  | Lebar hasil rectify (makin kecil makin cepat)   |
| `STABILITY_FRAMES`         | 3       | (streaming mode) frame konsisten sebelum TTS    |
| `COOLDOWN_SECONDS`         | 1.0 s   | (streaming mode) jeda antar TTS                 |
| `MAX_PROCESS_FPS`          | 10      | (streaming mode) batas pipeline per detik       |
| `AUTO_CALIBRATE`           | False   | Aktifkan setelah hue_ranges diverifikasi        |

---

## Keterbatasan Sistem (penting untuk sidang)

1. **"Asli" bukan autentikasi penuh.**
   Sistem memverifikasi dimensi fisik, warna dominan, dan angka nominal
   sesuai standar BI. Tidak mendeteksi fitur keamanan UV, benang pengaman,
   tanda air, atau microprinting. Uang palsu dengan ukuran dan warna
   yang benar dapat lolos.

2. **Deteksi angka terbatas pada template yang tersedia.**
   Template untuk Rp 100.000, Rp 50.000, Rp 20.000. Nominal lain
   menggunakan fallback AR + warna.

3. **Harus dikalibrasi per kamera.**
   Nilai HSV berbeda antar kamera dan kondisi pencahayaan.

4. **Background harus kontras dan polos.**
   Background bermotif menghasilkan false contour.

5. **Snapshot mode memerlukan kestabilan tangan.**
   Kontur harus stabil 5 frame berturut-turut. Jika tangan terlalu
   goyang, snapshot tidak terpicu.

---

## Output TTS

| Kondisi                     | Output Suara                              |
|:---------------------------|:------------------------------------------|
| Terdeteksi, valid           | "Lima Puluh Ribu Rupiah, Asli"           |
| Terdeteksi, warna mismatch  | "Seratus Ribu Rupiah, Mencurigakan atau Palsu" |
| Tidak ada kontur            | "Uang Tidak Terlihat, Dekatkan Kamera"   |
| Aspek rasio tidak cocok     | "Uang Tidak Dikenali atau Palsu"         |
