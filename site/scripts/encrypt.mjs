// Builds site/public/data/auth.json (password verifier) and kit.enc (encrypted
// application-kit bundle) from generate/output/drafts.json.
//
// Usage:  PASSWORD='the-password' npm run encrypt
// Must be re-run whenever the password changes or drafts are regenerated.
import { webcrypto as crypto } from 'node:crypto'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const ITERATIONS = 310000
const here = dirname(fileURLToPath(import.meta.url))
const dataDir = join(here, '..', 'public', 'data')
const draftsPath = join(here, '..', '..', 'generate', 'output', 'drafts.json')

const password = process.env.PASSWORD
if (!password) {
  console.error('Set PASSWORD env var, e.g.  PASSWORD="..." npm run encrypt')
  process.exit(1)
}

const b64 = (buf) => Buffer.from(buf).toString('base64')

const salt = crypto.getRandomValues(new Uint8Array(16))
const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits'])
const keyBits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: ITERATIONS, hash: 'SHA-256' }, material, 256)
const verifier = await crypto.subtle.digest('SHA-256', keyBits)

mkdirSync(dataDir, { recursive: true })
writeFileSync(join(dataDir, 'auth.json'), JSON.stringify({ salt: b64(salt), verifier: b64(verifier), iterations: ITERATIONS }))

const drafts = existsSync(draftsPath) ? JSON.parse(readFileSync(draftsPath, 'utf8')) : {}
const key = await crypto.subtle.importKey('raw', keyBits, 'AES-GCM', false, ['encrypt'])
const iv = crypto.getRandomValues(new Uint8Array(12))
const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(JSON.stringify(drafts)))
writeFileSync(join(dataDir, 'kit.enc'), JSON.stringify({ iv: b64(iv), ct: b64(ct) }))

console.log(`auth.json + kit.enc written (${Object.keys(drafts).length} job kits encrypted)`)
