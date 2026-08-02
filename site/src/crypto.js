// Password → AES-GCM key via PBKDF2. The personal application-kit bundle is
// genuinely encrypted (repo + Pages are public), so the password wall is real
// protection for Elise's drafts, not just a UI gate.

const ITERATIONS = 310000

const b64ToBytes = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
const bytesToB64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)))

export async function deriveKeyBytes(password, saltB64) {
  const enc = new TextEncoder()
  const material = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, [
    'deriveBits',
  ])
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: b64ToBytes(saltB64), iterations: ITERATIONS, hash: 'SHA-256' },
    material,
    256
  )
  return new Uint8Array(bits)
}

export async function verifierOf(keyBytes) {
  const digest = await crypto.subtle.digest('SHA-256', keyBytes)
  return bytesToB64(digest)
}

export async function decryptBundle(keyBytes, { iv, ct }) {
  const key = await crypto.subtle.importKey('raw', keyBytes, 'AES-GCM', false, ['decrypt'])
  const plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64ToBytes(iv) },
    key,
    b64ToBytes(ct)
  )
  return JSON.parse(new TextDecoder().decode(plain))
}

export { bytesToB64, b64ToBytes }
