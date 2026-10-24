// Check Am backend client. Set VITE_API_URL (e.g. a tunnel URL) to point the UI at another server.
export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

// Photos can't go through sessionStorage/history, so they wait here between the scan and checking pages.
const pendingFiles = new Map()
export function setPendingFiles(id, files) { pendingFiles.set(id, files || []) }
export function takePendingFiles(id) {
  const files = pendingFiles.get(id) || []
  pendingFiles.delete(id)
  return files
}

const CATEGORY_WORDS = [
  ['drug', ['drug', 'medicine', 'medication', 'tablet', 'capsule', 'syrup', 'pharma', 'antibiotic', 'malaria']],
  ['cosmetic', ['cosmetic', 'skincare', 'skin', 'cream', 'lotion', 'soap', 'toothpaste', 'perfume', 'hair', 'beauty']],
  ['spirits', ['spirit', 'whisky', 'whiskey', 'vodka', 'gin', 'brandy', 'alcohol', 'liquor']],
  ['water', ['water']],
  ['drink', ['drink', 'beverage', 'juice', 'soda', 'beer', 'wine', 'malt', 'energy']],
  ['food', ['food', 'snack', 'milk', 'noodle', 'rice', 'biscuit', 'chocolate', 'oil', 'seasoning', 'chips']],
  ['herbal', ['herbal', 'herb', 'supplement', 'nutraceutical']],
  ['medical_device', ['device', 'pad', 'diaper', 'lancet', 'test kit', 'glove', 'syringe']],
  ['phone', ['phone', 'smartphone', 'tablet pc', 'ipad', 'modem', 'pos']],
  ['electrical', ['cable', 'wire', 'socket', 'extension', 'bulb', 'switch', 'electrical', 'breaker']],
  ['electronics', ['electronic', 'tv', 'television', 'fridge', 'freezer', 'laptop', 'charger', 'speaker', 'generator']],
  ['auto_part', ['auto', 'car', 'tyre', 'tire', 'brake', 'engine', 'spare part']],
  ['building_material', ['cement', 'rod', 'roofing', 'tile', 'paint', 'pipe', 'building']],
  ['fashion', ['fashion', 'shoe', 'sneaker', 'bag', 'belt', 'watch', 'shirt', 'cloth', 'wear']],
]

export function toCategory(text) {
  const t = String(text || '').toLowerCase().trim()
  if (!t) return undefined
  for (const [cat, words] of CATEGORY_WORDS) if (cat === t || words.some((w) => t.includes(w))) return cat
  return 'other'
}

// The scan form's field names -> the API's field names
export function toFields(product = {}) {
  const f = {
    brand: product.brand,
    name: product.productName,
    variant: product.variant,
    category: toCategory(product.category),
    nafdac_no: product.nafdacNumber,
    batch: product.batchNumber,
    expiry: product.expiryDate,
    mfg_date: product.manufactureDate,
    barcode: product.barcode,
    imei: product.imei,
    imei_device: product.imeiDevice,
    son_marks: product.sonNumber ? [product.sonNumber] : undefined,
    seller: product.seller,
    price_ngn: product.price,
  }
  return Object.fromEntries(Object.entries(f).filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== ''))
}

async function handle(res) {
  if (res.ok) return res.json()
  let msg = `${res.status} ${res.statusText}`
  try { const j = await res.json(); msg = j.detail || msg } catch { /* not JSON */ }
  throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
}

export async function verify({ files = [], product = {}, situation = 'BEFORE_BUYING', location = '', research = false }) {
  const body = new FormData()
  for (const file of files) if (file && file.type?.startsWith('image/')) body.append('files', file, file.name)
  const fields = toFields(product)
  if (Object.keys(fields).length) body.append('fields', JSON.stringify(fields))
  body.append('situation', situation === 'ALREADY_BOUGHT' ? 'already_bought' : 'before_buying')
  body.append('research', research ? 'true' : 'false')
  if (location) body.append('state', location)
  return handle(await fetch(`${API_URL}/verify`, { method: 'POST', body }))
}

export async function researchScan(scanId) {
  return handle(await fetch(`${API_URL}/scans/${encodeURIComponent(scanId)}/research`, { method: 'POST' }))
}

export async function report({ scanId, location, seller, note }) {
  return handle(await fetch(`${API_URL}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scan_id: scanId, state: location || null, seller: seller || null, note: note || null }),
  }))
}

export async function confirmNapams(file, expectedRegNo) {
  const body = new FormData()
  body.append('screenshot', file, file.name)
  if (expectedRegNo) body.append('expected_reg_no', expectedRegNo)
  return handle(await fetch(`${API_URL}/confirm-napams`, { method: 'POST', body }))
}

export const NAPAMS_URL = 'https://registration.nafdac.gov.ng/#verify'
