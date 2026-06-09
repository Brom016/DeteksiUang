graph TD
    %% Definisi Gaya Node
    classDef user/os fill:#264653,stroke:#fff,stroke-width:2px,color:#fff;
    classDef app fill:#2a9d8f,stroke:#fff,stroke-width:2px,color:#fff;
    classDef logic fill:#e9c46a,stroke:#333,stroke-width:2px,color:#333;
    classDef output fill:#e76f51,stroke:#fff,stroke-width:2px,color:#fff;

    %% Alur User Flow
    A([User: Membuka Aplikasi via Perintah Suara / Shortcut]) :::user/os --> B[App: Mengaktifkan Kamera & Mengeluarkan Panduan Suara] :::app
    B --> C[App: Memberikan Getaran Pendek sebagai Tanda Siap Memindai] :::app
    
    C --> D([User: Menaruh Uang di Depan Kamera HP]) :::user/os
    D --> E[App: Mengambil Gambar Secara Otomatis Saat Objek Terdeteksi] :::app
    
    E --> F{Sistem PCD: Apakah Fisik Kertas Uang Terdeteksi?} :::logic
    
    %% Cabang Tidak Terdeteksi
    F -- Tidak --> G[App: Mengeluarkan Suara 'Uang Tidak Terlihat, Dekatkan Kamera'] :::app
    G --> H[App: Memberikan Getaran Panjang 1x] :::app
    H --> D
    
    %% Cabang Terdeteksi
    F -- Ya --> I[App: Mengeluarkan Suara 'Memproses...'] :::app
    I --> J[Sistem PCD: Pemotongan, Perhitungan Rasio & Ekstraksi Warna] :::logic
    
    J --> K{Sistem PCD: Apakah Uang Sesuai Standar Nominal BI?} :::logic
    
    %% Hasil Keputusan
    K -- Sesuai --> L[Output: Mengeluarkan Suara Nominal 'Seratus Ribu Rupiah'] :::output
    K -- Sesuai --> M[Output: Mengeluarkan Suara Status 'Asli'] :::output
    
    K -- Tidak Sesuai / Mencurigakan --> N[Output: Mengeluarkan Suara 'Uang Tidak Dikenali atau Mencurigakan'] :::output
    K -- Tidak Sesuai / Mencurigakan --> O[Output: Memberikan Getaran Putus-putus Melengking] :::output
    
    %% Akhir Alur
    L --> P([User: Selesai Transaksi / Mengantongi Uang]) :::user/os
    M --> P
    N --> Q([User: Meminta Uang Kembalian Lain ke Penjual]) :::user/os
    O --> Q
    
    P --> R([Selesai: Sistem Kembali ke Mode Siaga]) :::app
    Q --> R