/**
 * Rebuild the SAS Excel input from the archived World Bank Country API response.
 * Usage: node tools/build_metadata.mjs [project-root] [optional-preview.png] [optional-range]
 * Requires @oai/artifact-tool. No network request is made by this script.
 * Source: https://api.worldbank.org/v2/country?format=json&per_page=400
 * All source records and string values are retained. is_aggregate is derived
 * solely from region.id === 'NA'; classifications are download-time metadata.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const projectRoot = path.resolve(process.argv[2] || path.join(path.dirname(fileURLToPath(import.meta.url)), '..'));
const raw = JSON.parse(await fs.readFile(path.join(projectRoot, 'data/raw/countries.json'), 'utf8'));
if (!Array.isArray(raw) || raw.length !== 2 || raw[0].pages !== 1 || raw[1].length !== raw[0].total) {
  throw new Error('Expected a complete, single-page World Bank Country API response.');
}
const header = ['iso3', 'country_name', 'region_id', 'region', 'income_group', 'is_aggregate'];
const records = raw[1].map(r => [r.id, r.name, r.region.id, r.region.value, r.incomeLevel.value, Number(r.region.id === 'NA')])
  .sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
if (new Set(records.map(r => r[0])).size !== records.length) throw new Error('Duplicate World Bank economy codes.');
const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Economies');
const endRow = records.length + 1;
sheet.getRange(`A1:F${endRow}`).values = [header, ...records];
sheet.getRange(`A1:F${endRow}`).format.font = {name: 'Arial', size: 10};
sheet.getRange(`A1:F${endRow}`).format.verticalAlignment = 'center';
sheet.getRange(`A1:F${endRow}`).format.rowHeight = 21;
sheet.getRange('A1:F1').format = {
  fill: '#263B53', font: {name: 'Arial', size: 10, color: '#FFFFFF', bold: true},
  horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 24,
};
sheet.getRange(`A2:E${endRow}`).setNumberFormat('@');
sheet.getRange(`F2:F${endRow}`).setNumberFormat('0');
sheet.getRange(`F2:F${endRow}`).format.horizontalAlignment = 'right';
sheet.getRange(`A1:A${endRow}`).format.columnWidth = 10;
sheet.getRange(`B1:B${endRow}`).format.columnWidth = 55;
sheet.getRange(`B2:B${endRow}`).format.wrapText = true;
sheet.getRange(`C1:C${endRow}`).format.columnWidth = 12;
sheet.getRange(`D1:D${endRow}`).format.columnWidth = 50;
sheet.getRange(`E1:E${endRow}`).format.columnWidth = 24;
sheet.getRange(`F1:F${endRow}`).format.columnWidth = 16;
for (let i = 0; i < records.length; i += 1) {
  if (records[i][1].length > 50) sheet.getRange(`A${i + 2}:F${i + 2}`).format.rowHeight = 36;
}
sheet.freezePanes.freezeRows(1);
sheet.showGridLines = false;
workbook.recalculate();
const check = await workbook.inspect({kind: 'table', range: 'Economies!A1:F8', include: 'values,formulas', tableMaxRows: 8, tableMaxCols: 6});
console.log(check.ndjson);
const errors = await workbook.inspect({kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: {useRegex: true, maxResults: 20}});
console.log(errors.ndjson);
if (process.argv[3]) {
  const preview = await workbook.render({sheetName: 'Economies', range: process.argv[4] || 'A1:F12', scale: 1.4, format: 'png'});
  await fs.writeFile(path.resolve(process.argv[3]), new Uint8Array(await preview.arrayBuffer()));
}
const outputDir = path.join(projectRoot, 'data/input');
await fs.mkdir(outputDir, {recursive: true});
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outputDir, 'economies.xlsx'));
console.log(JSON.stringify({records: records.length, aggregateRecords: records.filter(r => r[5] === 1).length, maxUtf8Bytes: Object.fromEntries(header.slice(0, 5).map((h, i) => [h, Math.max(...records.map(r => Buffer.byteLength(r[i], 'utf8')))]))}, null, 2));
