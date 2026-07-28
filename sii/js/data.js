const siteData = {
    siteName: "NUSA PACKING INDONESIA",
    siteTagline: "Pabrik Plastik Packaging Murah dan Terpercaya di Indonesia",
    since: 2013,

    // ========== HERO (Beranda) ==========
    hero: {
        subtitle: "SINCE 2013",
        title: "Pabrik Plastik Packaging<br>Terpercaya di Indonesia",
        description: "Memproduksi berbagai macam kemasan plastik berkualitas tinggi untuk industri makanan, minuman, retail, farmasi, dan manufaktur. Solusi packaging lengkap dengan harga kompetitif.",
        buttons: {
            catalog: "Lihat Katalog Produk",
            contact: "Hubungi Kami"
        },
        bgImage: "img/bg.jpg"             
    },

    // ========== STATS (Beranda) ==========
    stats: [
        { number: 11,  label: "Tahun Pengalaman" },
        { number: 200, label: "Klien Aktif" },
        { number: 1000, label: "Varian Produk" },
        { number: 30,  label: "Mesin Produksi" }
    ],

    // ========== ABOUT (Beranda) ==========
    about: {
        tag: "TENTANG KAMI",
        title: "Mitra Terpercaya untuk Kebutuhan Plastik Packaging Anda",
        paragraphs: [
            "NUSA PACKING INDONESIA adalah pabrik plastik packaging yang berlokasi di kawasan industri strategis. Sejak tahun 2013, kami telah melayani berbagai perusahaan dari skala UKM hingga korporasi multinasional.",
            "Kami mengkhususkan diri dalam produksi berbagai jenis kemasan plastik seperti <strong>Polymailer, Bubble Mailer, Zipper, Bubble Wrap,</strong> dan masih banyak lagi."
        ],
        features: [
            "Bahan baku bersertifikat",
            "Teknologi mesin modern & otomatis",
            "Custom desain & ukuran sesuai permintaan",
            "Harga pabrik langsung, tanpa perantara",
            "Pengiriman tepat waktu ke seluruh Indonesia",
            "Tim QC profesional di setiap tahap produksi"
        ],
        button: "Jelajahi Produk Kami",
        badge: "ISO 9641:2013",
        image: "img/pt.jpg",
        imageAlt: "Fasilitas Pabrik NUSA PACKING INDONESIA"
    },

    // ========== KATEGORI PRODUK (Beranda) ==========
    productCategories: [
        {
            name: "Polymailer",
            icon: "fa-envelope",
            image: "",
            description: "Kantong Polymailer dalam berbagai warna, ukuran, dan ketebalan."
        },
        {
            name: "Bubble Mailer",
            icon: "fa-envelope-open-text",
            image: "",
            description: "Kantong bubble mailer dengan lapisan gelembung pelindung di dalam."
        },
        {
            name: "Zipper Bag",
            icon: "fa-bag-shopping",
            image: "",
            description: "Kemasan plastik zipper lock untuk makanan, kosmetik, dan retail."
        },
        {
            name: "Bubble Wrap",
            icon: "fa-shield-halved",
            image: "",
            description: "Plastik gelembung pelindung untuk pengamanan barang fragile."
        },
        {
            name: "OPP Tape",
            icon: "fa-tape",
            image: "",
            description: "Lakban bening dan coklat untuk packing dan sealing karton."
        }
    ],

    // ========== WHY US (Beranda) ==========
    whyUs: {
        tag: "KEUNGGULAN KAMI",
        title: "Mengapa Memilih Kami?",
        description: "Kami berkomitmen memberikan produk dan layanan terbaik untuk mitra bisnis.",
        items: [
            { number: "01", title: "Kualitas Terjamin", description: "Setiap produk melalui quality control ketat dan menggunakan bahan baku pilihan." },
            { number: "02", title: "Harga Kompetitif", description: "Harga langsung dari pabrik tanpa perantara, memberikan nilai terbaik untuk Anda." },
            { number: "03", title: "Custom Produk", description: "Melayani custom ukuran, ketebalan, warna, hingga cetak logo sesuai kebutuhan." },
            { number: "04", title: "Kapasitas Besar", description: "Didukung 30+ mesin modern dengan kapasitas produksi hingga ratusan ton per bulan." }
        ]
    },

    // ========== CTA (Beranda) ==========
    cta: {
        title: "Butuh Plastik Packaging Berkualitas?",
        description: "Konsultasikan kebutuhan Anda dengan tim kami. Dapatkan penawaran harga terbaik hari ini!",
        buttons: {
            contact: "Hubungi Kami Sekarang",
            catalog: "Lihat Katalog Lengkap"
        }
    },

    // ========== FOOTER (Semua Halaman) ==========
    footer: {
        about: "Pabrik plastik packaging terpercaya melayani kebutuhan kemasan plastik berkualitas untuk berbagai industri di seluruh Indonesia.",
        products: ["Polymailer", "Bubble Mailer", "Zipper Bag", "Bubble Wrap", "OPP Tape"],
        pages: [
            { name: "Beranda", url: "/" },
            { name: "Katalog", url: "/katalog/" },
            { name: "Hubungi Kami", url: "/kontak/" }
        ],
        social: {
            whatsapp: "https://wa.me/6281230586587",
            instagram: "#",
            facebook: "#",
            email: "mailto:arifkacipz@gmail.com"
        }
    },

    // ========== KONTAK (Footer & Halaman Kontak) ==========
    contact: {
        address: "Laksana Business Park Blok LA-32, Jl. Raya Kalibaru, Laksana, Kecamatan Pakuhaji, Kabupaten Tangerang, Banten 15570",
        phone: "+62 812-3058-6587",
        whatsapp: "+62 812-3058-6587",
        email: "arifkacipz@gmail.com"
    },

    // ========== WHATSAPP FLOATING BUTTON ==========
    waLink: "https://wa.me/6281230586587",

    // ========== HALAMAN KATALOG ==========
    catalogPage: {
        title: "Katalog Produk Plastik",
        description: "Lebih dari 1000 varian produk siap memenuhi kebutuhan packaging Anda.",
        filterLabels: ["Semua", "Polymailer", "Bubble Mailer", "Zipper", "OPP", "Bubble Wrap", "Other"],
        filterValues: ["all", "poly", "mailer", "zip", "opp", "wrap", "other"]
        
    },

    // ========== HALAMAN KONTAK ==========
    contactPage: {
        title: "Hubungi Kami",
        description: "Kami siap membantu kebutuhan plastik packaging Anda.",
        formLabels: {
            name: "Nama Lengkap",
            email: "Email",
            wa: "Nomor WhatsApp",
            subject: "Subjek",
            message: "Pesan",
            submit: "Kirim Pesan"
        },
        mapEmbedUrl: "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3967.417281101296!2d106.6157982719013!3d-6.074332493911725!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2e6a017c59549c8d%3A0xd2c8a2a3964b0470!2sPT.%20Swiftpack%20Industry%20Indonesia!5e0!3m2!1sid!2sid!4v1784601709371!5m2!1sid!2sid"
    }
};
