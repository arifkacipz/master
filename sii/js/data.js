const siteData = {
    siteName: "PT Plastik Packindo Sejahtera",
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
        bgImage: "img/hero-bg.jpg"   // kosongkan "" jika tidak ada
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
            "PT Plastik Packindo Sejahtera adalah pabrik plastik packaging yang berlokasi di kawasan industri strategis. Sejak tahun 2005, kami telah melayani berbagai perusahaan dari skala UKM hingga korporasi multinasional.",
            "Kami mengkhususkan diri dalam produksi berbagai jenis kemasan plastik seperti <strong>Polymailer, bubma, zipper, bubble wrap,</strong> dan masih banyak lagi."
        ],
        features: [
            "Bahan baku food-grade bersertifikat",
            "Teknologi mesin modern & otomatis",
            "Custom desain & ukuran sesuai permintaan",
            "Harga pabrik langsung, tanpa perantara",
            "Pengiriman tepat waktu ke seluruh Indonesia",
            "Tim QC profesional di setiap tahap produksi"
        ],
        button: "Jelajahi Produk Kami",
        badge: "ISO 9001:2015",
        image: "img/about-factory.jpg",  // foto pabrik
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
            { number: "01", title: "Kualitas Terjamin", description: "Setiap produk melalui quality control ketat dan bahan baku food-grade." },
            { number: "02", title: "Harga Kompetitif", description: "Harga langsung pabrik tanpa perantara." },
            { number: "03", title: "Custom Produk", description: "Custom ukuran, ketebalan, hingga berbagai pilihan warna." },
            { number: "04", title: "Kapasitas Besar", description: "30+ mesin modern, kapasitas ratusan ton/bulan." }
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
            email: "mailto:sales@packindosejahtera.co.id"
        }
    },
    
    contact: {
        address: "Laksana Business Park Blok LA-12, LA-12A, LA-32, Jl. Raya Kalibaru, Laksana, Kecamatan Pakuhaji, Kabupaten Tangerang, Banten 15570",
        whatsapp: "+62 812-3058-6587",
        email: "sales@packindosejahtera.co.id"
    },
    
    waLink: "https://wa.me/6281230586587",
    
    catalogPage: {
        title: "Katalog Produk Plastik",
        description: "Lebih dari 2000 varian produk siap memenuhi kebutuhan packaging Anda",
        filterLabels: ["Semua", "Polymailer", "Bubble Mailer", "Zipper", "Bubble Wrap", "Other"],
        filterValues: ["all", "bag", "bubma", "zip", "bubble", "other"],
        products: [
            { name: "Polymailer Hitam-1", category: "bag", icon: "fa-bag-shopping", image: "img/hitam1.jpeg", desc: "Kantong Polymailer dengan warna Hitam Glossy." },
            { name: "Polymailer Hitam-2", category: "bag", icon: "fa-bag-shopping", image: "img/hitam2.png", desc: "Kantong Polymailer dengan warna Hitam Doff." },
            { name: "Polymailer Putih Hitam-8", category: "bag", icon: "fa-bag-shopping", image: "img/putihhitam8.jpeg", desc: "Kantong Polymailer dengan bagian luar berwarna putih dan bagian dalam berwarna hitam." },
            { name: "Polymailer Putih Hitam-11", category: "bag", icon: "fa-bag-shopping", image: "img/putihhitam8.jpeg", desc: "Kantong Polymailer dengan bagian luar berwarna putih dan bagian dalam berwarna hitam." },
            { name: "Botol PET 330ml", category: "bottle", icon: "fa-bottle-water", image: "", desc: "Botol minum PET bening 330ml standar." },
            { name: "Botol HDPE 500ml", category: "bottle", icon: "fa-bottle-water", image: "", desc: "Botol HDPE untuk kosmetik/farmasi." },
            { name: "Stretch zip 50cm", category: "zip", icon: "fa-roll", image: "", desc: "Stretch zip lebar 50cm, tebal 20 micron." },
            { name: "Stretch zip 30cm", category: "zip", icon: "fa-roll", image: "", desc: "Stretch zip mini untuk packing manual." },
            { name: "Standing Pouch Zipper 12x20", category: "pouch", icon: "fa-envelopes-bulk", image: "", desc: "Pouch aluminium foil + zipper untuk kopi." },
            { name: "Standing Pouch Bening 15x25", category: "pouch", icon: "fa-envelopes-bulk", image: "", desc: "Pouch transparan klip zipper untuk snack." },
            { name: "Bubble Wrap 1.2m", category: "bubble", icon: "fa-shield-halved", image: "", desc: "Bubble roll lebar 120cm, gelembung 10mm." },
            { name: "Bubble Wrap Kecil 30cm", category: "bubble", icon: "fa-shield-halved", image: "", desc: "Bubble wrap kecil untuk pengiriman elektronik." }
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
        mapEmbedUrl: "https://maps.app.goo.gl/HnEfuAJW8Ye9DeNn6"
    }
};