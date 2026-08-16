import { neon } from '@neondatabase/serverless';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  let databaseUrl = process.env.DATABASE_URL || process.env.NEON_DATABASE_URL || '';
  databaseUrl = databaseUrl.replace(/\s+/g, '');
  if (!databaseUrl) {
    return res.status(500).json({ error: 'DATABASE_URL environment variable is missing.' });
  }

  try {
    const { userId = 'anonymous', version, part, score, totalQuestions, percentage, isPass, isRealExam, timeSpent } = req.body;
    const sql = neon(databaseUrl);

    await sql`
      INSERT INTO exam_results (user_id, version, part, score, total_questions, percentage, is_pass, is_real_exam, time_spent_seconds)
      VALUES (${userId}, ${version}, ${parseInt(part, 10)}, ${parseInt(score, 10)}, ${parseInt(totalQuestions, 10)}, ${parseInt(percentage, 10)}, ${isPass}, ${isRealExam}, ${parseInt(timeSpent, 10)});
    `;

    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Submit Result Error:', error);
    return res.status(500).json({ error: error.message });
  }
}
