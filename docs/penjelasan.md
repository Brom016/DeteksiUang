# Penjelasan Sistem Verifikasi Uang Kertas Rupiah TE 2022

## 1. Latar Belakang

Penyandang tunanetra mengalami kesulitan dalam mengidentifikasi nominal uang kertas secara mandiri. Uang kertas Rupiah memiliki perbedaan ukuran, warna, dan angka nominal yang dapat dideteksi secara visual, namun keterbatasan penglihatan menghalangi akses terhadap informasi tersebut. Bank Indonesia telah menerbitkan uang TE (Tahun Emisi) 2022 dengan desain yang lebih kontras dan jarak dimensi 5 mm antar nominal (lebih besar dari TE 2016 yang hanya 2 mm), sehingga lebih mudah dibedakan secara mekanis. Sistem ini dikembangkan untuk memanfaatkan perbedaan dimensi, warna, dan angka nominal tersebut sebagai alat bantu identifikasi bagi penyandang tunanetra.

## 2. Tujuan

- **Mendeteksi** nominal uang kertas Rupiah TE 2022 secara real-time dari kamera
- **Mengidentifikasi** 7 nominal: Rp 1.000, Rp 2.000, Rp 5.000, Rp 10.000, Rp 20.000, Rp 50.000, dan Rp 100.000
- **Memverifikasi** keaslian berdasarkan kesesuaian dimensi, warna dominan, dan angka nominal
- **Memberikan** output suara (TTS) dalam Bahasa Indonesia yang dapat dipahami tunanetra
- **Bekerja** secara otomatis tanpa tombol — arahkan uang ke kamera, sistem mendeteksi dan mengumumkan hasil

## 3. Batasan

- **Bukan autentikasi penuh**: Sistem hanya memverifikasi dimensi, warna, dan angka nominal. Tidak mendeteksi fitur keamanan seperti UV, benang pengaman, tanda air, atau microprinting.
- **Bergantung pada template**: Deteksi angka hanya akurat untuk nominal yang memiliki template. Saat ini tersedia untuk Rp 100.000, Rp 50.000, dan Rp 20.000.
- **Kalibrasi HSV diperlukan per kamera**: Nilai hue berbeda antar perangkat kamera dan kondisi pencahayaan.
- **Background harus kontras dan polos**: Background bermotif atau terlalu ramai menghasilkan false contour.
- **Uang tertekuk atau kusut** sulit directify dengan akurat sehingga deteksi gagal.
- **Snapshot mode memerlukan kestabilan tangan**: Kontur harus stabil selama 5 frame berturut-turut agar snapshot terpicu.

## 4. Metode

Sistem menggunakan pendekatan _Computer Vision_ dengan tiga modalitas utama yang saling melengkapi:

### a. Deteksi Angka Nominal (_Template Matching_)
- **Metode**: `cv2.matchTemplate` dengan `TM_CCOEFF_NORMED` pada citra _grayscale_.
- **ROI**: Pojok kanan-bawah gambar uang yang sudah diluruskan (_rectified_), tempat angka nominal tercetak.
- **Multi-skala**: 12 skala (0.55× – 1.55×) untuk toleransi variasi ukuran akibat jarak kamera.
- **Sliding window**: 9 posisi ROI (±2% offset) untuk mengkompensasi ketidaktepatan rectification.
- **Threshold**: Confidence ≥ 0.30 diterima sebagai kecocokan.

### b. Analisis Warna (_HSV Color Matching_)
- **Ruang warna**: HSV (_Hue, Saturation, Value_) — hue lebih robust terhadap perubahan pencahayaan.
- **Dominant hue**: Hue yang paling sering muncul di seluruh piksel uang.
- **Hue fraction**: Persentase piksel yang berada dalam rentang hue target.
- **Bobot**: Digunakan sebagai faktor verifikasi (bobot 0.35) atau sebagai fallback penuh saat angka tidak terdeteksi.

### c. Analisis Geometri (_Aspect Ratio_)
- **Aspek rasio** = panjang / lebar (lebar seragam 65 mm).
- TE 2022 memiliki step 5 mm → ΔAR ≈ 0.077 antar nominal (sangat mudah dibedakan).
- Invariant terhadap jarak kamera — hanya bergantung pada proporsi, bukan ukuran absolut.
- Berfungsi sebagai _cross-validation gate_: jika AR hasil deteksi tidak cocok dengan AR nominal yang diklaim oleh number detection (ar_s < 0.1), maka hasil number detection dianggap false positive dan sistem fallback ke AR + warna.

## 5. Urutan Proses

### Snapshot Mode (Default)

```
1. Baca frame dari kamera (~30 fps)
2. quick_contour_detect():
   a. Grayscale + Gaussian Blur
   b. Canny Edge Detection
   c. findContours → cari kontur persegi terbesar
3. Jika kontur ditemukan:
   → streak++ (counter stabilitas)
4. Jika streak ≥ 5 frame berturut-turut:
   → Ambil snapshot (frame saat itu)
   → Proses pipeline penuh SEKALI:
      a. rectify: minAreaRect → order_points → warpPerspective (640 px)
      b. detect_number_enhanced():
         - 12 skala × 9 sliding ROI = 108 kombinasi matching
         - Ambil confidence tertinggi
      c. classify():
         - Jika angka terdeteksi (confidence ≥ 0.30):
           → Hitung color_score, ar_score
           → Cross-validate: AR cocok? (ar_s ≥ 0.1)
             - Ya → combined = num_conf × 0.65 + color_s × 0.35
             - Tidak → false positive, fallback ke AR + warna
         - Jika angka tidak terdeteksi / false positive:
           → Iterasi semua 7 nominal
           → Skor = ar_s × (0.6 + 0.4 × color_s)
           → Ambil nominal dengan skor tertinggi
      d. Verifikasi keaslian:
         - Butuh color_score > 0.15 ATAU number_ok
         - Combined score > 0.2
         - Jika ya → "Asli", jika tidak → "Mencurigakan"
      e. Output TTS
   → Cooldown 2 detik
5. Jika kontur tidak ditemukan:
   → streak = 0
   → Tampilkan "Arahkan uang ke kamera"
```

### Streaming Mode (Alternatif — SNAPSHOT_MODE = False)

```
1. Baca frame dari kamera (max 10 fps processing)
2. Pipeline penuh tiap frame (rectify + number + classify)
3. Masukkan hasil ke StabilityBuffer (buffer 3 frame)
4. Jika 3 hasil berturut-turut identik → output TTS
5. Cooldown 1 detik
```

## 6. Implementasi

### Struktur Kode

| File | Fungsi |
|:-----|:-------|
| `config.py` | Semua konstanta: database 7 nominal TE 2022, parameter tuning, mode detection |
| `preprocessor.py` | Grayscale, Gaussian Blur, Canny edge detection |
| `rectifier.py` | minAreaRect, order_points, warpPerspective (rectify ke 640 px) |
| `feature_extractor.py` | Ekstraksi aspek rasio dan fraksi hue dari gambar rectified |
| `number_detector.py` | `detect_number()` (standar) dan `detect_number_enhanced()` (snapshot: 12 skala × 9 ROI) |
| `classifier.py` | Logika klasifikasi dan skoring dengan AR cross-validation |
| `calibrator.py` | Auto-kalibrasi HSV (default nonaktif) |
| `tts_engine.py` | Text-to-Speech via pyttsx3 / gTTS |
| `pipeline.py` | `quick_contour_detect()` (fast path) dan `process_frame()` (pipeline penuh) |
| `main.py` | Entry point: snapshot mode, streaming mode, image mode, calibration mode |
| `test_pipeline.py` | 16 pengujian otomatis gambar sintetis |

### Database Nominal

Database 7 nominal TE 2022 dengan dimensi terverifikasi:

| Nominal | AR | Hue | Step |
|:--------|:--:|:---:|:----:|
| Rp 100.000 | 2.3231 | Merah (0–10) | — |
| Rp 50.000 | 2.2462 | Biru (100–130) | 5 mm |
| Rp 20.000 | 2.1692 | Hijau (40–85) | 5 mm |
| Rp 10.000 | 2.0923 | Ungu (130–160) | 5 mm |
| Rp 5.000 | 2.0154 | Coklat (8–28) | 5 mm |
| Rp 2.000 | 1.9385 | Abu-abu Hijau (70–100) | 5 mm |
| Rp 1.000 | 1.8615 | Perak/Abu-abu (all hues, S < 35) | 5 mm |

### Parameter Kunci

| Parameter | Nilai | Keterangan |
|:----------|:-----:|:-----------|
| `WARP_OUTPUT_WIDTH` | 640 px | Lebar hasil rectifikasi (makin kecil makin cepat) |
| `NUMBER_WEIGHT` | 0.65 | Bobot number detection jika terdeteksi & divalidasi |
| `COLOR_WEIGHT` | 0.35 | Bobot color matching |
| `TEMPLATE_MATCH_THRESHOLD` | 0.30 | Threshold minimum template matching |
| `ASPECT_RATIO_TOLERANCE` | 0.025 | ±0.025 dari AR target (step nominal 0.077) |
| `SNAPSHOT_CONTOUR_STREAK` | 5 | Jumlah frame kontur stabil sebelum snapshot |
| `SNAPSHOT_COOLDOWN` | 2.0 s | Jeda antar snapshot |

### Template Angka

Template gambar angka nominal disimpan di `assets/templates/{value}.png`. Template adalah hasil crop asli dari pojok kanan-bawah gambar uang referensi, disimpan dalam format grayscale. Matching dilakukan di grayscale dengan multi-skala untuk mengakomodasi variasi ukuran.

## 7. Kesimpulan dan Saran

### Kesimpulan

Sistem berhasil mengidentifikasi 7 nominal uang kertas Rupiah TE 2022 menggunakan kombinasi template matching angka, analisis warna HSV, dan aspek rasio geometri. Pendekatan snapshot mode (deteksi kontur cepat tiap frame, pipeline penuh sekali saat stabil) memberikan keseimbangan antara kecepatan dan akurasi — kontur diperiksa ~30 fps tanpa membebani CPU, pipeline penuh dijalankan hanya 1× per snapshot dengan 108 kombinasi matching untuk akurasi maksimal. AR cross-validation mencegah false positive dari template matching yang keliru. Seluruh 16 pengujian pipeline lulus (7 unit + 7 integrasi + 1 wrong-colour + 1 blank).

### Saran Pengembangan

1. **Lebih banyak template**: Tambahkan template untuk Rp 10.000, Rp 5.000, Rp 2.000, dan Rp 1.000 agar deteksi angka mencakup semua nominal.
2. **Peningkatan rectification**: Implementasi _perspective correction_ yang lebih robust (misal 4-point transform dengan RANSAC) untuk menangani uang tertekuk.
3. **Model deep learning**: Ganti template matching dengan CNN ringan (MobileNet / Tiny YOLO) untuk deteksi angka yang lebih akurat dan tidak memerlukan template.
4. **Autentikasi lanjutan**: Integrasi deteksi fitur keamanan seperti watermark, security thread, atau _ultraviolet_ response untuk verifikasi yang lebih menyeluruh.
5. **Mode multi-emisi**: Dukungan untuk TE 2016 dan TE 2022 secara simultan dengan deteksi tahun emisi otomatis.
6. **Kalibrasi otomatis**: Aktifkan auto-calibrate setelah hue_ranges diverifikasi — sistem akan belajar dan menyempurnakan nilai hue dari deteksi yang percaya diri.
7. **Akselerasi hardware**: Pindahkan pipeline ke GPU (CUDA/OpenCL) untuk mempercepat matching, terutama jika menambah jumlah template.
