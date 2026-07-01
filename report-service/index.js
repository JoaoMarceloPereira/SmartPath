const express = require('express');
const { Pool } = require('pg');
const PDFDocument = require('pdfkit');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8085;

const pool = new Pool({
  user: process.env.PGUSER || 'smartpath',
  host: process.env.PGHOST || 'postgres',
  database: process.env.PGDATABASE || 'smartpath',
  password: process.env.PGPASSWORD || 'smartpath123',
  port: process.env.PGPORT || 5432,
});

// Busca estatísticas das decisões de trânsito
async function getTrafficStats() {
  const result = await pool.query(`
    SELECT
      intersection_id,
      COUNT(*)                          AS total_decisions,
      AVG(green_time)::numeric(10,2)    AS avg_green_time_s,
      MAX(green_time)                   AS max_green_time_s,
      MIN(green_time)                   AS min_green_time_s,
      COUNT(*) FILTER (WHERE action = 'ABERTURA_EMERGENCIA') AS emergency_count
    FROM traffic_decisions
    GROUP BY intersection_id
    ORDER BY intersection_id
  `);
  return result.rows;
}

// Busca histórico das últimas N decisões
async function getRecentHistory(limit = 20) {
  const result = await pool.query(`
    SELECT timestamp, intersection_id, action, green_time, pressure_score
    FROM traffic_decisions
    ORDER BY timestamp DESC
    LIMIT $1
  `, [limit]);
  return result.rows;
}

// GET /reports/stats — Estatísticas em JSON
app.get('/reports/stats', async (req, res) => {
  try {
    const stats = await getTrafficStats();
    res.json({ stats });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch stats', detail: err.message });
  }
});

// GET /reports/history — Histórico em JSON
app.get('/reports/history', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 20;
    const history = await getRecentHistory(limit);
    res.json({ history });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch history', detail: err.message });
  }
});

// GET /reports/pdf — Gera relatório completo em PDF
app.get('/reports/pdf', async (req, res) => {
  try {
    const [stats, history] = await Promise.all([getTrafficStats(), getRecentHistory(50)]);

    const doc = new PDFDocument({ margin: 50 });

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename="smartpath-report.pdf"');
    doc.pipe(res);

    // ── Capa
    doc.fontSize(28).font('Helvetica-Bold').text('SmartPath', { align: 'center' });
    doc.fontSize(16).font('Helvetica').text('Relatório de Trânsito Inteligente', { align: 'center' });
    doc.moveDown();
    doc.fontSize(11).text(`Gerado em: ${new Date().toLocaleString('pt-BR')}`, { align: 'center' });
    doc.moveDown(2);

    // ── Seção: Estatísticas por Cruzamento
    doc.fontSize(16).font('Helvetica-Bold').text('Estatísticas por Cruzamento');
    doc.moveTo(50, doc.y).lineTo(550, doc.y).stroke();
    doc.moveDown(0.5);

    if (stats.length === 0) {
      doc.fontSize(11).font('Helvetica').text('Nenhuma decisão registrada ainda.');
    } else {
      stats.forEach(s => {
        doc.fontSize(13).font('Helvetica-Bold').text(`Cruzamento: ${s.intersection_id}`);
        doc.fontSize(11).font('Helvetica')
          .text(`  • Total de decisões:      ${s.total_decisions}`)
          .text(`  • Emergências detectadas:  ${s.emergency_count}`)
          .text(`  • Tempo verde médio:       ${s.avg_green_time_s}s`)
          .text(`  • Tempo verde máx:         ${s.max_green_time_s}s`)
          .text(`  • Tempo verde mín:         ${s.min_green_time_s}s`);
        doc.moveDown(0.8);
      });
    }

    doc.moveDown();

    // ── Seção: Histórico Recente
    doc.fontSize(16).font('Helvetica-Bold').text('Histórico Recente (últimas 50 decisões)');
    doc.moveTo(50, doc.y).lineTo(550, doc.y).stroke();
    doc.moveDown(0.5);

    if (history.length === 0) {
      doc.fontSize(11).font('Helvetica').text('Nenhum histórico disponível.');
    } else {
      history.forEach((h, i) => {
        const ts = new Date(h.timestamp).toLocaleString('pt-BR');
        doc.fontSize(10).font('Helvetica')
          .text(`${i + 1}. [${ts}] ${h.intersection_id} | Ação: ${h.action} | Verde: ${h.green_time}s | Pressão: ${parseFloat(h.pressure_score).toFixed(2)}`);
      });
    }

    doc.end();
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to generate PDF', detail: err.message });
  }
});

app.get('/health', (req, res) => res.json({ status: 'UP' }));

app.listen(PORT, () => console.log(`Report Service rodando na porta ${PORT}`));
