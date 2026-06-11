graph TD
    A([Mulai: Kamera Mengambil Foto Uang]) --> B[Pre-processing: Konversi ke Grayscale]
    B --> C[Deteksi Tepi: Canny Edge Detection]
    C --> D[Pencarian Kontur: findContours]
    D --> E{Apakah Kontur Uang Ditemukan?}
    
    E -- Tidak --> F[Output Suara: Objek Tidak Terdeteksi, Silakan Coba Lagi]
    F --> A
    
    E -- Ya --> G[Ambil 4 Titik Sudut Kontur: minAreaRect]
    G --> H[Transformasi Geometri: Warp Perspective]
    H --> I[Hasil: Citra Uang Lurus & Terpotong Perfect]
    
    I --> J1[Hitung Aspek Rasio: Panjang / Lebar]
    I --> J2[Konversi Ruang Warna ke HSV]
    
    J1 --> K[Identifikasi Nominal Berdasarkan Dimensi]
    J2 --> L[Hitung Histogram Dominan pada Komponen Hue]
    
    K --> M[Validasi Silang: Kecocokan Ukuran & Warna Dominan]
    L --> M
    
    M --> N{Apakah Data Valid & Sesuai Standar?}
    
    N -- Tidak --> O[Output Suara: Uang Mencurigakan atau Palsu]
    N -- Ya --> P[Output Suara: Menyebutkan Nominal & Keaslian Uang]
    
    O --> Q([Selesai])
    P --> Q([Selesai])