import { neon } from '@neondatabase/serverless';

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  let databaseUrl = process.env.DATABASE_URL || process.env.NEON_DATABASE_URL || '';
  databaseUrl = databaseUrl.replace(/\s+/g, '');

  if (!databaseUrl) {
    return res.status(500).json({ error: 'DATABASE_URL environment variable is missing on Vercel.' });
  }

  try {
    const { version = '2026', part = '1' } = req.query;
    const sql = neon(databaseUrl);

    const rows = await sql`
      SELECT 
        id, 
        qid, 
        topic, 
        question_en, 
        question_th, 
        options_en, 
        options_th, 
        answer_index, 
        explanation_en, 
        explanation_th 
      FROM questions 
      WHERE version = ${version} AND part = ${parseInt(part, 10)}
      ORDER BY id ASC;
    `;

    // Format response to ensure proper array JSON types
    const questions = rows.map(r => ({
      id: r.id,
      qid: r.qid,
      topic: r.topic,
      question_en: r.question_en,
      question_th: r.question_th,
      options_en: typeof r.options_en === 'string' ? JSON.parse(r.options_en) : r.options_en,
      options_th: typeof r.options_th === 'string' ? JSON.parse(r.options_th) : r.options_th,
      answer_index: r.answer_index,
      explanation_en: r.explanation_en,
      explanation_th: r.explanation_th
    }));

    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=86400');
    return res.status(200).json(questions);
  } catch (error) {
    console.error('Vercel Neon API Error:', error);
    return res.status(500).json({ error: error.message });
  }
}
