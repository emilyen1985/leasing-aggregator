const https = require('https');

const SUPABASE_URL = 'znzxbhzkeymyrwmaycrd.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpuenhiaHprZXlteXJ3bWF5Y3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyOTU5NDgsImV4cCI6MjA5MTg3MTk0OH0.CKpae6h5XKifu3189daNRqY9_uFs1DoELh1skEzKa4Q';

module.exports = function(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');

  const offset = req.query.offset || 0;
  const limit = req.query.limit || 1000;
  const path = `/rest/v1/listings?select=*&order=date_updated.desc&limit=${limit}&offset=${offset}`;

  const options = {
    hostname: SUPABASE_URL,
    path: path,
    method: 'GET',
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': 'Bearer ' + SUPABASE_KEY,
      'Accept': 'application/json'
    }
  };

  const proxyReq = https.request(options, function(proxyRes) {
    const chunks = [];
    proxyRes.on('data', function(chunk) { chunks.push(chunk); });
    proxyRes.on('end', function() {
      const body = Buffer.concat(chunks).toString('utf8');
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.status(200).send(body);
    });
  });

  proxyReq.on('error', function(e) {
    res.status(500).json({ error: e.message });
  });

  proxyReq.end();
};
