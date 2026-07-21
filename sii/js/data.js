const siteData = {
    siteName: "NUSA PACKING INDONESIA",
    siteTagline: "Pabrik Plastik Packaging Terpercaya di Indonesia",
    since: 2005,
    
    hero: {
        subtitle: "SINCE 2005",
        title: "Pabrik Plastik Packaging<br>Terpercaya di Indonesia",
        description: "Memproduksi berbagai macam kemasan plastik berkualitas tinggi untuk industri makanan, minuman, retail, farmasi, dan manufaktur. Solusi packaging lengkap dengan harga kompetitif.",
        buttons: {
            catalog: "Lihat Katalog Produk",
            contact: "Hubungi Kami"
        },
        bgImage: "img/bg.jpg"
    },
    
    stats: [
        { number: 11, label: "Tahun Pengalaman" },
        { number: 200, label: "Klien Aktif" },
        { number: 1000, label: "Varian Produk" },
        { number: 30, label: "Mesin Produksi" }
    ],
    
    about: {
        tag: "TENTANG KAMI",
        title: "Mitra Terpercaya untuk Kebutuhan Plastik Packaging Anda",
        paragraphs: [
            "NUSA PACKING INDONESIA adalah pabrik plastik packaging yang berlokasi di kawasan industri strategis. Sejak tahun 2005, kami telah melayani berbagai perusahaan dari skala UKM hingga korporasi multinasional.",
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
        badge: "ISO 9001:2015",
        image: "img/pt.jpg",
        imageAlt: "Fasilitas Pabrik"
    },
    
    // Kategori di homepage – bisa pakai foto atau ikon
    productCategories: [
        { name: "Polymailer", icon: "fa-bag-shopping", image: "", description: "Kantong plastik Polymailer dalam berbagai warna dan ukuran." },
        { name: "Zipper", icon: "fa-envelopes-bulk", image: "", description: "Kemasan plastik dengan zipper untuk berbagai kebutuhan." },
        { name: "Bubble Wrap", icon: "fa-shield-halved", image: "", description: "Plastik gelembung pelindung untuk barang elektronik dan fragile." }
    ],
    
    whyUs: {
        tag: "KEUNGGULAN KAMI",
        title: "Mengapa Memilih Kami?",
        description: "Kami berkomitmen memberikan produk dan layanan terbaik",
        items: [
            { number: "01", title: "Kualitas Terjamin", description: "Setiap produk melalui quality control ketat." },
            { number: "02", title: "Harga Kompetitif", description: "Harga langsung pabrik tanpa perantara." },
            { number: "03", title: "Custom Produk", description: "Custom ukuran, ketebalan, hingga berbagai pilihan warna." },
            { number: "04", title: "Kapasitas Besar", description: "30+ mesin modern, kapasitas ratusan ton perbulan." }
        ]
    },
    
    cta: {
        title: "Butuh Plastik Packaging Berkualitas?",
        description: "Konsultasikan kebutuhan Anda dengan tim kami. Dapatkan penawaran harga terbaik hari ini!",
        buttons: {
            contact: "Hubungi Kami Sekarang",
            catalog: "Lihat Katalog Lengkap"
        }
    },
    
    footer: {
        about: "Pabrik plastik packaging terpercaya melayani kebutuhan kemasan plastik berkualitas untuk berbagai industri di seluruh Indonesia.",
        products: ["Polymailer", "Bubble Mailer", "Zipper", "Bubble wrap"],
        pages: [
            { name: "Beranda", url: "index.html" },
            { name: "Katalog", url: "katalog/index.html" },
            { name: "Hubungi Kami", url: "kontak/index.html" }
        ],
        social: {
            whatsapp: "#",
            instagram: "#",
            facebook: "#",
            email: "mailto:arifkacipz@gmail.com"
        }
    },
    
    contact: {
        address: "Laksana Business Park Blok LA-32, Jl. Raya Kalibaru, Laksana, Kecamatan Pakuhaji, Kabupaten Tangerang, Banten 15570",
        whatsapp: "+62 812-3058-6587",
        email: "arifkacipz@gmail.com"
    },
    
    waLink: "https://wa.me/6281230586587",
    
    catalogPage: {
        title: "Katalog Produk Plastik",
        description: "Lebih dari 2000 varian produk siap memenuhi kebutuhan packaging Anda",
        filterLabels: ["Semua", "Polymailer", "Bubble Mailer", "Zipper", "OPP", "Bubble Wrap", "Other"],
        filterValues: ["all", "poly", "mailer", "zip", "opp", "bubble", "other"],
        products: [
            { name: "Polymailer Hitam-1", category: "bag", icon: "fa-bag-shopping", image: "../img/hitam1.jpeg", desc: "Kantong Polymailer dengan warna Hitam Glossy." },
            { name: "Polymailer Hitam-2", category: "bag", icon: "fa-bag-shopping", image: "../img/hitam2.png", desc: "Kantong Polymailer dengan warna Hitam Doff." },
            { name: "Polymailer Putih Hitam-8", category: "bag", icon: "fa-bag-shopping", image: "../img/putihhitam8.jpeg", desc: "Kantong Polymailer dengan bagian luar berwarna putih dan bagian dalam berwarna hitam." },
            { name: "Polymailer Putih Hitam-11", category: "bag", icon: "fa-bag-shopping", image: "../img/putihhitam8.jpeg", desc: "Kantong Polymailer dengan bagian luar berwarna putih dan bagian dalam berwarna hitam." },
        ]
    },
    
    contactPage: {
        title: "Hubungi Kami",
        description: "Kami siap membantu kebutuhan plastik packaging Anda",
        formLabels: {
            name: "Nama Lengkap",
            email: "Email",
            subject: "Subjek",
            message: "Pesan",
            submit: "Kirim Pesan"
        },
        mapEmbedUrl: "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3967.417281101296!2d106.6157982719013!3d-6.074332493911725!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2e6a017c59549c8d%3A0xd2c8a2a3964b0470!2sPT.%20Swiftpack%20Industry%20Indonesia!5e0!3m2!1sid!2sid!4v1784601709371!5m2!1sid!2sid"
    }
};
