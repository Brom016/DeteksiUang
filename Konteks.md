# PROPOSAL / DRAFT PROYEK PENGOLAHAN CITRA DIGITAL (PCD)

## IDENTITAS PROYEK
* **Judul Proyek:** Sistem Verifikasi Keaslian dan Nilai Nominal Uang Kertas Rupiah Emisi 2022 Berbasis Konversi Ruang Warna HSV dan Geometri Citra Sebagai Alat Bantu Tunanetra
* **Tema Utama:** Pengenalan Objek Berdasar Warna & Bentuk
* **Target Pengguna:** Penyandang Tunanetra / Gangguan Penglihatan (*Low Vision*)
* **Platform Implementasi:** Mobile (Flutter/Android) atau Desktop Application (Python)

---

## 1. LATAR BELAKANG & URGENSI
Penyandang tunanetra sering menghadapi tantangan besar dan risiko penipuan saat melakukan transaksi tunai secara mandiri. Meskipun Bank Indonesia telah menyertakan fitur *Blind Code* (pola garis timbul) pada uang Rupiah, fitur fisik ini memiliki kelemahan utama: **pola timbul akan mengikis, menipis, dan menjadi rata** seiring seringnya uang berpindah tangan, lecek, atau terlipat. 

Di sisi lain, solusi berbasis *Deep Learning* (AI) saat ini sering kali menuntut spesifikasi perangkat (*hardware*) yang tinggi, ruang penyimpanan besar untuk model data, dan ketergantungan pada koneksi internet (*cloud*). 

Proyek ini hadir sebagai solusi alternatif yang **efisien dan ringan**. Dengan memanfaatkan teknik Pengolahan Citra Digital (PCD) konvensional, sistem dapat mengenali nominal dan keaslian uang secara *offline* di perangkat dengan spesifikasi rendah sekalipun, hanya dengan membaca karakteristik fisik yang konsisten dari Bank Indonesia.

---

## 2. PARAMETER PARAMETRIK UANG RUPIAH EMISI 2022
Efisiensi proyek ini didasarkan pada dua standarisasi utama dari Bank Indonesia (khususnya pada Emisi 2022):

1. **Karakteristik Geometri (Bentuk):** Bank Indonesia mendesain uang Rupiah dengan selisih panjang yang sangat konsisten. Setiap pecahan yang nilainya mengecil akan memiliki ukuran yang lebih pendek dengan **selisih panjang tepat 2 mm**. Sedangkan untuk lebarnya, semua pecahan memiliki ukuran yang sama, yaitu 65 mm.
2. **Karakteristik Kromatik (Warna):** Setiap pecahan memiliki warna dominan yang sangat kontras satu sama lain ketika diekstrak menggunakan komponen *Hue* pada ruang warna **HSV** (Merah untuk Rp100.000, Biru untuk Rp50.000, Hijau untuk Rp20.000, dst).

---

## 3. ARSITEKTUR SISTEM & PIPELINE PCD
Sistem akan memproses citra masukan melalui tahapan linear tanpa melalui proses *training* data yang rumit:
``[Input Foto Uang] ➔ [Canny Edge & Contours] ➔ [Warp Perspective] ➔ [Hitung Aspek Rasio & HSV] ➔ [Text-to-Speech]``

### A. Preprocessing & Segmentasi Citra
* **Tujuan:** Menemukan dan memisahkan objek uang dari latar belakang tempat uang diletakkan.
* **Metode:** 1. Mengubah citra masukan menjadi *Grayscale*.
  2. Menerapkan **Canny Edge Detection** untuk mendeteksi tepian luar uang.
  3. Menggunakan fungsi `findContours` untuk mengunci area kontur terbesar yang merepresentasikan fisik uang kertas.

### B. Rectification (Warp Perspective Transform)
* **Tujuan:** Meluruskan posisi foto uang yang miring atau terdistorsi akibat sudut pengambilan kamera yang tidak tegak lurus.
* **Metode:** Menggunakan fungsi `minAreaRect` untuk mengambil 4 titik sudut terkecil dari kontur uang, lalu menerapkan **Warp Perspective Transform** untuk menghasilkan gambar persegi panjang yang simetris dan rata (*cropped & flattened*).

### C. Ekstraksi Fitur & Identifikasi Nominal
Setelah citra uang lurus sempurna, sistem menjalankan dua kalkulasi secara paralel:
1. **Analisis Aspek Rasio (Geometri):** Sistem membagi nilai Panjang dengan Lebar dari gambar yang telah diluruskan. 
   $$\text{Aspek Rasio} = \frac{\text{Panjang (piksel)}}{\text{Lebar (piksel)}}$$
   Karena lebar asli semua uang adalah 65 mm, nilai rasio ini akan konstan dan menjadi pembeda valid untuk mengidentifikasi dimensi uang tanpa terpengaruh jarak jauh-dekatnya kamera.
2. **Analisis Histogram Warna (Kromatik):** Mengonversi gambar hasil potongan ke ruang warna **HSV**. Sistem kemudian menghitung histogram dominan pada komponen *Hue* (H) untuk mengunci warna utama uang, sehingga terhindar dari bias intensitas cahaya ruangan.

### D. Output Aksesibilitas
* Hasil identifikasi nominal dan keaslian dasar dikonversi menjadi data audio menggunakan pustaka **Text-to-Speech (TTS)** agar dapat langsung didengar oleh pengguna tunanetra (Contoh output: *"Seratus Ribu Rupiah, Asli"*).

---

## 4. ANALISIS Kegagalan & ANTISIPASI (Pertahanan Sidang/Tugas)

* **Potensi Kegagalan 1:** Jarak kamera yang berubah-ubah membuat ukuran piksel uang berubah (Uang Rp10k yang dekat terlihat sama panjang dengan uang Rp100k yang jauh).
  * **Antisipasi Teknik TI:** Sistem tidak menghitung panjang mutlak piksel, melainkan menggunakan **Aspek Rasio (Perbandingan Panjang terhadap Lebar)**. Rasio perbandingan ini akan selalu tetap sama berapapun jarak kameranya.
* **Potensi Kegagalan 2:** Perubahan intensitas cahaya ruangan (lampu kuning vs cahaya matahari terik) merusak nilai warna asli.
  * **Antisipasi Teknik TI:** Pengolahan warna dilakukan pada ruang warna **HSV**, bukan RGB. Komponen *Hue* (H) pada HSV memisahkan informasi warna murni dari komponen *Value* (V) atau kecerahan, sehingga algoritma jauh lebih stabil dari fluktuasi cahaya.

---

## 5. KEUNGGULAN & EFISIENSI PROYEK

* **Efisiensi Koding:** Berjalan menggunakan fungsi-fungsi dasar matematika matriks OpenCV. Tidak memerlukan pembuatan model AI, instalasi library *Deep Learning* yang berat, maupun komputasi GPU.
* **Efisiensi Dataset:** Pengumpulan data sangat mudah dan murah. Cukup mengambil beberapa sampel foto uang asli dari berbagai nominal dengan kamera HP untuk menentukan ambang batas (*thresholding*) nilai HSV dan Aspek Rasio.
* **Bobot Akademis Kuat:** Meskipun kodingannya relatif sederhana, proyek ini memiliki nilai fungsi yang tinggi di mata dosen karena menerapkan konsep transformasi geometri (`Warp Perspective`) dan pengolahan ruang warna yang tepat untuk memecahkan masalah sosial nyata (*Human-Centered Technology*).
