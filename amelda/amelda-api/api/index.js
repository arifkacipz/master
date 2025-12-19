const mysql = require('mysql2/promise');

export default async function handler(req, res) {
    // Izinkan akses dari domain GitHub Pages Anda
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();

    // Konfigurasi TiDB (Ambil dari TiDB Console)
    const dbConfig = {
        host: 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
        user: '4Lf1oLZHxYutf7y.root',
        password: 'dqrUuaSe4G9xINu4',
        database: 'test',
        port: 4000,
        ssl: { minVersion: 'TLSv1.2', rejectUnauthorized: false }
    };

    const connection = await mysql.createConnection(dbConfig);

    if (req.method === 'POST') {
        const { nama, kehadiran, ucapan } = req.body;
        await connection.execute(
            'INSERT INTO rsvp_ucapan (nama, kehadiran, ucapan) VALUES (?, ?, ?)',
            [nama, kehadiran, ucapan]
        );
        return res.status(200).json({ status: 'success' });
    } 
    
    if (req.method === 'GET') {
        const [rows] = await connection.execute('SELECT * FROM rsvp_ucapan ORDER BY id DESC');
        return res.status(200).json(rows);
    }
}