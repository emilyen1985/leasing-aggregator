export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  
  const SUPABASE_URL = 'https://znzxbhzkeymyrwmaycrd.supabase.co';
  const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpuenhiaHprZXlteXJ3bWF5Y3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyOTU5NDgsImV4cCI6MjA5MTg3MTk0OH0.CKpae6h5XKifu3189daNRqY9_uFs1DoELh1skEzKa4Q';

  const offset = req.query.offset || 0;
  const limit = req.query.limit || 1000;
  
  const url = `${SUPABASE_URL}/rest/v1/listings?select=*&order=date_updated.desc&limit=${limit}&offset=${offset}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`
      }
    });
    const data = await response.json();
    res.status(200).json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
