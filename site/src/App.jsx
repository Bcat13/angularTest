import React, { useEffect, useMemo, useRef, useState } from 'react'
import { deriveKeyBytes, verifierOf, decryptBundle, bytesToB64, b64ToBytes } from './crypto.js'

const DATA = (path) => `${import.meta.env.BASE_URL}data/${path}`

const TYPE_LABELS = {
  postdoc: 'Postdoc',
  tenure_track: 'Tenure-track',
  visiting: 'Visiting',
  lecturer: 'Lecturer / Teaching',
  other: 'Other',
}
const CLASS_LABELS = {
  liberal_arts: 'Liberal arts',
  research_university: 'Research univ.',
  doctoral_professional: 'Doctoral/prof.',
  masters: "Master's",
  baccalaureate_diverse: 'Baccalaureate',
  research_institute: 'Research institute',
  national_lab: 'National lab',
  unknown: 'Unclassified',
  other: 'Other',
}
const STATUSES = ['none', 'interested', 'preparing', 'applied', 'passed']
const STATUS_LABELS = { none: '—', interested: '★ Interested', preparing: '✏️ Preparing', applied: '✅ Applied', passed: '🚫 Passed' }

const DEFAULT_FILTERS = {
  types: ['postdoc', 'tenure_track'],
  classes: [],
  airport: 'ok', // ok | any
  subfield: 'ok', // ok (combinatorics/open-field only) | any
  country: 'all',
  newOnly: false,
  hidePast: true,
  hidePassed: true,
  q: '',
  sort: 'deadline',
}

export default function App() {
  const [key, setKey] = useState(() => {
    const saved = sessionStorage.getItem('jf_key')
    return saved ? b64ToBytes(saved) : null
  })
  if (!key) return <Login onKey={setKey} />
  return <Main keyBytes={key} onLock={() => { sessionStorage.removeItem('jf_key'); setKey(null) }} />
}

function Login({ onKey }) {
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const auth = await (await fetch(DATA('auth.json'))).json()
      const kb = await deriveKeyBytes(pw, auth.salt)
      if ((await verifierOf(kb)) !== auth.verifier) {
        setErr('Wrong password.')
        setBusy(false)
        return
      }
      sessionStorage.setItem('jf_key', bytesToB64(kb))
      onKey(kb)
    } catch {
      setErr('Could not load auth data.')
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo">∑</div>
        <h1>Elise&rsquo;s Job Finder</h1>
        <p className="muted">Academic math positions, filtered for you.</p>
        <input
          type="password"
          placeholder="Password"
          value={pw}
          autoFocus
          onChange={(e) => setPw(e.target.value)}
        />
        <button disabled={busy || !pw}>{busy ? 'Checking…' : 'Enter'}</button>
        {err && <p className="err">{err}</p>}
      </form>
    </div>
  )
}

function useLocalStatus() {
  const [map, setMap] = useState(() => JSON.parse(localStorage.getItem('jf_status') || '{}'))
  const set = (id, patch) => {
    setMap((m) => {
      const next = { ...m, [id]: { ...(m[id] || {}), ...patch } }
      if (next[id].status === 'none' && !next[id].notes) delete next[id]
      localStorage.setItem('jf_status', JSON.stringify(next))
      return next
    })
  }
  return [map, set, setMap]
}

function Main({ keyBytes, onLock }) {
  const [jobs, setJobs] = useState(null)
  const [generated, setGenerated] = useState('')
  const [kit, setKit] = useState({})
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [openId, setOpenId] = useState(() => location.hash.slice(1) || null)
  const [status, setStatus, setStatusMap] = useLocalStatus()

  useEffect(() => {
    fetch(DATA('jobs.json'))
      .then((r) => r.json())
      .then((d) => { setJobs(d.jobs); setGenerated(d.generated) })
    fetch(DATA('kit.enc'))
      .then((r) => (r.ok ? r.json() : null))
      .then((enc) => (enc ? decryptBundle(keyBytes, enc) : {}))
      .then(setKit)
      .catch(() => setKit({}))
  }, [keyBytes])

  useEffect(() => {
    const onHash = () => setOpenId(location.hash.slice(1) || null)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const weekAgo = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - 7)
    return d.toISOString().slice(0, 10)
  }, [])
  const today = new Date().toISOString().slice(0, 10)

  const shown = useMemo(() => {
    if (!jobs) return []
    let list = jobs.filter((j) => {
      if (filters.types.length && !filters.types.includes(j.position_type)) return false
      if (filters.classes.length && !filters.classes.includes(j.inst_class)) return false
      if (filters.airport === 'ok' && j.airport_ok !== true) return false
      if (filters.subfield === 'ok' && j.subfield_ok === false) return false
      if (filters.country !== 'all' && j.country !== filters.country) return false
      if (filters.newOnly && j.first_seen < weekAgo) return false
      if (filters.hidePast && j.deadline && j.deadline < today) return false
      if (filters.hidePassed && status[j.id]?.status === 'passed') return false
      if (filters.q) {
        const hay = `${j.institution} ${j.title} ${j.city} ${j.state} ${j.subject}`.toLowerCase()
        if (!hay.includes(filters.q.toLowerCase())) return false
      }
      return true
    })
    if (filters.sort === 'deadline')
      list.sort((a, b) => (a.deadline || '9999').localeCompare(b.deadline || '9999'))
    else if (filters.sort === 'newest') list.sort((a, b) => (b.first_seen || '').localeCompare(a.first_seen || ''))
    else list.sort((a, b) => a.institution.localeCompare(b.institution))
    return list
  }, [jobs, filters, status, weekAgo, today])

  if (!jobs) return <div className="login-wrap"><p className="muted">Loading jobs…</p></div>

  const openJob = openId && jobs.find((j) => j.id === openId)

  return (
    <div className="layout">
      <header className="topbar">
        <div>
          <strong>∑ Elise&rsquo;s Job Finder</strong>
          <span className="muted sml"> · {jobs.length} jobs · updated {generated}</span>
        </div>
        <div className="topbar-actions">
          <ExportImport statusMap={status} setStatusMap={setStatusMap} />
          <button className="ghost" onClick={onLock}>Lock</button>
        </div>
      </header>

      <Filters filters={filters} setFilters={setFilters} shownCount={shown.length} />

      <main className="list">
        {shown.map((j) => (
          <JobCard key={j.id} job={j} status={status[j.id]} kit={kit[j.id]} onOpen={() => (location.hash = j.id)} today={today} weekAgo={weekAgo} />
        ))}
        {shown.length === 0 && <p className="muted center">Nothing matches these filters.</p>}
      </main>

      {openJob && (
        <JobDetail
          job={openJob}
          kitEntry={kit[openJob.id]}
          status={status[openJob.id]}
          setStatus={(patch) => setStatus(openJob.id, patch)}
          onClose={() => (location.hash = '')}
        />
      )}
    </div>
  )
}

function Chip({ active, onClick, children }) {
  return (
    <button className={`chip ${active ? 'on' : ''}`} onClick={onClick}>
      {children}
    </button>
  )
}

function toggle(arr, v) {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]
}

function Filters({ filters, setFilters, shownCount }) {
  const f = filters
  const set = (patch) => setFilters({ ...f, ...patch })
  return (
    <div className="filters">
      <div className="filter-row">
        <span className="filter-label">Position</span>
        {Object.entries(TYPE_LABELS).map(([k, label]) => (
          <Chip key={k} active={f.types.includes(k)} onClick={() => set({ types: toggle(f.types, k) })}>{label}</Chip>
        ))}
      </div>
      <div className="filter-row">
        <span className="filter-label">School</span>
        {Object.entries(CLASS_LABELS).map(([k, label]) => (
          <Chip key={k} active={f.classes.includes(k)} onClick={() => set({ classes: toggle(f.classes, k) })}>{label}</Chip>
        ))}
      </div>
      <div className="filter-row">
        <span className="filter-label">More</span>
        <Chip active={f.airport === 'ok'} onClick={() => set({ airport: f.airport === 'ok' ? 'any' : 'ok' })}>✈️ ≤55 mi of airport</Chip>
        <Chip active={f.subfield === 'ok'} onClick={() => set({ subfield: f.subfield === 'ok' ? 'any' : 'ok' })}>🎯 Combinatorics / open-field</Chip>
        <Chip active={f.country === 'US'} onClick={() => set({ country: f.country === 'US' ? 'all' : 'US' })}>🇺🇸 US</Chip>
        <Chip active={f.country === 'CA'} onClick={() => set({ country: f.country === 'CA' ? 'all' : 'CA' })}>🇨🇦 Canada</Chip>
        <Chip active={f.newOnly} onClick={() => set({ newOnly: !f.newOnly })}>🆕 New this week</Chip>
        <Chip active={f.hidePast} onClick={() => set({ hidePast: !f.hidePast })}>Hide past deadlines</Chip>
        <Chip active={f.hidePassed} onClick={() => set({ hidePassed: !f.hidePassed })}>Hide passed</Chip>
        <select value={f.sort} onChange={(e) => set({ sort: e.target.value })}>
          <option value="deadline">Sort: deadline</option>
          <option value="newest">Sort: newest</option>
          <option value="school">Sort: school</option>
        </select>
        <input className="search" placeholder="Search…" value={f.q} onChange={(e) => set({ q: e.target.value })} />
        <span className="muted sml count">{shownCount} shown</span>
      </div>
    </div>
  )
}

function DeadlineBadge({ deadline, today }) {
  if (!deadline) return <span className="badge gray">no deadline</span>
  const days = Math.round((new Date(deadline) - new Date(today)) / 86400000)
  if (days < 0) return <span className="badge gray">passed {deadline}</span>
  if (days <= 14) return <span className="badge red">due {deadline} · {days}d</span>
  if (days <= 45) return <span className="badge amber">due {deadline}</span>
  return <span className="badge green">due {deadline}</span>
}

function JobCard({ job, status, kit, onOpen, today, weekAgo }) {
  return (
    <div className="card" onClick={onOpen}>
      <div className="card-top">
        <div>
          <div className="inst">
            {job.institution}
            {job.first_seen >= weekAgo && <span className="badge blue sml-badge">NEW</span>}
          </div>
          <div className="title">{job.title}</div>
          <div className="meta muted">
            {job.city}, {job.state} {job.country === 'CA' ? '🇨🇦' : ''}
            {job.airport_miles != null
              ? ` · ✈️ ${job.nearest_airport} — ${job.airport_miles} mi`
              : ' · ✈️ unknown'}
          </div>
        </div>
        <div className="card-right">
          <span className={`badge ${job.position_type === 'postdoc' ? 'purple' : job.position_type === 'tenure_track' ? 'indigo' : 'gray'}`}>
            {TYPE_LABELS[job.position_type]}
          </span>
          <span className={`badge ${job.liberal_arts ? 'teal' : 'gray'}`}>{CLASS_LABELS[job.inst_class]}</span>
          {job.subfield === 'combinatorics' && <span className="badge green">combinatorics</span>}
          {job.subfield_ok === false && <span className="badge red">{job.subfield}</span>}
          <DeadlineBadge deadline={job.deadline} today={today} />
          {kit && <span className="badge gold">✍️ kit ready</span>}
          {status?.status && status.status !== 'none' && (
            <span className="badge outline">{STATUS_LABELS[status.status]}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function CopyBtn({ text, label = 'Copy' }) {
  const [done, setDone] = useState(false)
  return (
    <button
      className="ghost sml-btn"
      onClick={(e) => {
        e.stopPropagation()
        navigator.clipboard.writeText(text)
        setDone(true)
        setTimeout(() => setDone(false), 1500)
      }}
    >
      {done ? '✓ Copied' : label}
    </button>
  )
}

function JobDetail({ job, kitEntry, status, setStatus, onClose }) {
  const notesTimer = useRef(null)
  useEffect(() => {
    const onKeyDown = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  // save notes as the user types (debounced) — blur-only saving loses the
  // note if the page is refreshed while the textarea still has focus
  function saveNotes(value) {
    clearTimeout(notesTimer.current)
    notesTimer.current = setTimeout(() => setStatus({ notes: value }), 300)
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose}>×</button>
        <h2>{job.institution}</h2>
        <h3>{job.title}</h3>
        <p className="muted">
          {job.department && <>{job.department} · </>}
          {job.city}, {job.state}, {job.country}
          {job.airport_miles != null && (
            <> · ✈️ {job.nearest_airport} — {job.airport_miles} mi{job.airport_ok ? '' : ' (beyond 55 mi)'}</>
          )}
        </p>
        <p>
          <span className="badge indigo">{TYPE_LABELS[job.position_type]}</span>{' '}
          <span className={`badge ${job.liberal_arts ? 'teal' : 'gray'}`}>{CLASS_LABELS[job.inst_class]}</span>{' '}
          {job.deadline && <span className="badge amber">deadline {job.deadline}</span>}{' '}
          {job.subfield && job.subfield !== 'general' && (
            <span className={`badge ${job.subfield_ok ? 'green' : 'red'}`}>{job.subfield}</span>
          )}{' '}
          {job.subject && <span className="badge gray">{job.subject}</span>}
        </p>

        <div className="actions">
          <a className="btn primary" href={job.apply_url || job.url} target="_blank" rel="noreferrer">
            Open application ↗
          </a>
          <a className="btn" href={job.url} target="_blank" rel="noreferrer">
            View posting ↗
          </a>
          <select value={status?.status || 'none'} onChange={(e) => setStatus({ status: e.target.value })}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>
        <p className="muted sml">
          This site never submits anything for you — the buttons above just open the employer&rsquo;s
          own pages in a new tab.
        </p>

        <textarea
          className="notes"
          placeholder="Your notes on this job… (saved automatically)"
          defaultValue={status?.notes || ''}
          onChange={(e) => saveNotes(e.target.value)}
          onBlur={(e) => setStatus({ notes: e.target.value })}
        />

        {kitEntry ? (
          <div className="kit">
            <h4>✍️ Application kit</h4>
            {Object.entries(kitEntry).map(([k, v]) => (
              <div className="kit-item" key={k}>
                <div className="kit-head">
                  <strong>{k.replace(/_/g, ' ')}</strong>
                  <CopyBtn text={v} />
                </div>
                <pre>{v}</pre>
              </div>
            ))}
          </div>
        ) : (
          <div className="kit">
            <h4>✍️ Application kit</h4>
            <p className="muted sml">No pre-generated draft for this job yet. Ask Ben to run the generator, or copy the job description below into Claude with Elise&rsquo;s materials.</p>
          </div>
        )}

        {job.description && (
          <details open>
            <summary>Full posting text</summary>
            <pre className="desc">{job.description}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

function ExportImport({ statusMap, setStatusMap }) {
  function doExport() {
    const blob = new Blob([JSON.stringify(statusMap, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `job-statuses-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
  }
  function doImport() {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async () => {
      const text = await input.files[0].text()
      const parsed = JSON.parse(text)
      localStorage.setItem('jf_status', JSON.stringify(parsed))
      setStatusMap(parsed)
    }
    input.click()
  }
  return (
    <span>
      <button className="ghost" onClick={doExport}>Export</button>
      <button className="ghost" onClick={doImport}>Import</button>
    </span>
  )
}
