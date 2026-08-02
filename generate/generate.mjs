// Pre-drafts per-job application kits with the Claude API.
// Run locally only (materials + API key never leave this machine):
//
//   cd generate && npm install && node generate.mjs [--limit N] [--id mathjobs-12345]
//   then: cd ../site && PASSWORD='...' npm run encrypt
//
// Auth: ANTHROPIC_API_KEY env var (or an `ant auth login` profile).
import Anthropic from '@anthropic-ai/sdk'
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const jobsPath = join(here, '..', 'site', 'public', 'data', 'jobs.json')
const profilePath = join(here, '..', 'materials', 'elise_profile.md')
const systemPath = join(here, 'prompts', 'system.md')
const outPath = join(here, 'output', 'drafts.json')

const MODEL = 'claude-sonnet-5'

const args = process.argv.slice(2)
const limitIdx = args.indexOf('--limit')
const limit = limitIdx >= 0 ? Number(args[limitIdx + 1]) : Infinity
const onlyIds = args.filter((a, i) => args[i - 1] === '--id')

const profile = readFileSync(profilePath, 'utf8')
const systemPrompt = readFileSync(systemPath, 'utf8')
const { jobs } = JSON.parse(readFileSync(jobsPath, 'utf8'))
const drafts = existsSync(outPath) ? JSON.parse(readFileSync(outPath, 'utf8')) : {}

// Default: jobs matching the default filter that don't have a kit yet
let targets = jobs.filter(
  (j) =>
    ['postdoc', 'tenure_track'].includes(j.position_type) &&
    j.airport_ok &&
    j.subfield_ok !== false
)
if (onlyIds.length) targets = jobs.filter((j) => onlyIds.includes(j.id))
targets = targets.filter((j) => !drafts[j.id]).slice(0, limit)

console.log(`Generating kits for ${targets.length} jobs with ${MODEL}...`)
const client = new Anthropic()

function userPrompt(job) {
  const teachingFocused = job.liberal_arts || job.position_type === 'lecturer'
  return `# Candidate profile

${profile}

# The job posting

Institution: ${job.institution} (${job.inst_class.replace(/_/g, ' ')})
Title: ${job.title}
Position type: ${job.position_type}
Location: ${job.city}, ${job.state}, ${job.country}
Deadline: ${job.deadline || 'not stated'}
${job.subject ? `Subject: ${job.subject}` : ''}

Posting text:
${(job.description || '(no description available — rely on title and institution)').slice(0, 12000)}

# Task

This is a ${teachingFocused ? 'teaching-focused' : 'research-focused'} application. Produce:

1. **cover_letter** — a complete draft cover letter (350–500 words) tailored to this posting.
2. **fit_talking_points** — 4–6 bullet points on why the candidate fits THIS position specifically, usable in interviews or supplemental questions.
3. **application_checklist** — the materials this posting asks for (from its text), each with a one-line note on what the candidate should emphasize.

Format the response as exactly three markdown sections with the headers "## cover_letter", "## fit_talking_points", "## application_checklist".`
}

function parseSections(text) {
  const out = {}
  const parts = text.split(/^## +/m).filter(Boolean)
  for (const part of parts) {
    const nl = part.indexOf('\n')
    const key = part.slice(0, nl).trim()
    out[key] = part.slice(nl + 1).trim()
  }
  return out
}

const CONCURRENCY = 5
let done = 0
const queue = [...targets]
mkdirSync(dirname(outPath), { recursive: true })

async function worker() {
  for (let job = queue.shift(); job; job = queue.shift()) {
    try {
      const stream = client.messages.stream({
        model: MODEL,
        max_tokens: 16000,
        system: [{ type: 'text', text: systemPrompt, cache_control: { type: 'ephemeral' } }],
        messages: [{ role: 'user', content: userPrompt(job) }],
      })
      const message = await stream.finalMessage()
      if (message.stop_reason === 'refusal') {
        console.warn(`  refused: ${job.id}`)
        continue
      }
      const text = message.content.filter((b) => b.type === 'text').map((b) => b.text).join('\n')
      drafts[job.id] = parseSections(text)
      done++
      console.log(`  ✓ ${job.institution} — ${job.title} (${done}/${targets.length})`)
      writeFileSync(outPath, JSON.stringify(drafts, null, 1))
    } catch (err) {
      console.error(`  ✗ ${job.id}: ${err.message}`)
    }
  }
}

await Promise.all(Array.from({ length: CONCURRENCY }, worker))

console.log(`\nDone. ${done} kits written to ${outPath}`)
console.log(`Next: cd ../site && PASSWORD='<site password>' npm run encrypt`)
