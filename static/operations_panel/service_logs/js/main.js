(function() {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function toIso(dt) {
    if (!dt) return null;
    try { return new Date(dt).toISOString(); } catch(e) { return null; }
  }

  function fmt(dtIso) {
    if (!dtIso) return '';
    try {
      const d = new Date(dtIso);
      return d.toLocaleString();
    } catch (e) {
      return dtIso;
    }
  }

  async function fetchJSON(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  async function postJSON(url, data) {
    const csrftoken = getCookie('csrftoken');
    const r = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || ''
      },
      body: JSON.stringify(data || {})
    });
    const text = await r.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch (e) { /* ignore */ }
    if (!r.ok) {
      const msg = (payload && payload.error) ? payload.error : `HTTP ${r.status}`;
      throw new Error(msg);
    }
    return payload;
  }

  function renderHeader(header, log) {
    qs('#hdr-folio').textContent = header.folio || '';
    qs('#hdr-driver').textContent = header.driver_name || 'N/D';
    qs('#hdr-vehicle').textContent = header.vehicle || 'N/D';
    qs('#hdr-plates').textContent = header.vehicle_plates || 'N/D';
    qs('#hdr-origin').textContent = header.origin || 'N/D';
    qs('#hdr-destination').textContent = header.destination || 'N/D';
    qs('#hdr-departure').textContent = fmt(log.departure_datetime) || '—';
    qs('#hdr-arrival').textContent = fmt(log.arrival_datetime) || '—';
    const st = qs('#hdr-status');
    st.textContent = (log.status || '').replaceAll('_', ' ');
  }

  function filterActivitiesByDay(activities, day){
    if (!activities) return [];
    const start = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 0,0,0,0);
    const end = new Date(start.getTime()); end.setDate(end.getDate()+1);
    return activities.filter(a => {
      const s = new Date(a.started_at);
      const e = new Date(a.ended_at || a.started_at);
      return (s < end) && (e > start);
    });
  }

  function renderActivitiesList(activities) {
    const box = qs('#activities-list');
    if (!box) return;
    if (!activities || !activities.length) {
      box.innerHTML = '<div class="text-muted">Sin actividades registradas para este día.</div>';
      return;
    }
    const rows = activities.map(a => {
      return `<div class="py-1 border-bottom">
        <span class="badge bg-light text-dark">${a.activity_type}</span>
        <span class="ms-2">${fmt(a.started_at)} → ${fmt(a.ended_at)}</span>
        ${a.notes ? `<div class="small text-muted">${a.notes}</div>` : ''}
      </div>`;
    });
    box.innerHTML = rows.join('');
  }

  function renderTotals(totals) {
    const box = qs('#totals');
    if (!box) return;
    if (!totals) { box.innerHTML = ''; return; }
    const overall = totals.overall || {};
    const cats = ['DRIVING','PAUSE','AUXILIARY','EXCEPTION','REST'];
    const lines = cats.map(c => `<div><span class="fw-bold">${c}</span>: ${overall[c] || 0} h</div>`);
    lines.push(`<div class="mt-2"><span class="fw-bold">TOTAL</span>: ${overall['TOTAL'] || 0} h</div>`);
    box.innerHTML = lines.join('');
  }

  function pickDefaultDay(data){
    const cand = data.departure_datetime || (data.header && data.header.scheduled_departure_time) || (data.header && data.header.operation_date) || null;
    if (cand){
      const d = new Date(cand);
      if (!isNaN(d.getTime())) return new Date(d.getFullYear(), d.getMonth(), d.getDate());
    }
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), today.getDate());
  }

  async function init() {
    const app = qs('#service-log-app');
    if (!app) return;
    const logId = app.getAttribute('data-log-id');
    if (!logId) return;

    const url = `${window.location.origin}/operations/service-logs/${logId}/data/`;
    let data = null;
    let currentDay = null;
    let timeline = null;
    let selectedEvent = null;

    function updateDayLabel(){
      if (!timeline) return;
      const labelEl = qs('#day-label');
      labelEl.textContent = timeline.getDayLabel();
    }

    function setDay(d){
      currentDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      timeline.setDay(currentDay);
      updateDayLabel();
      // Clear hover time when switching day
      const ht = qs('#hover-time'); if (ht) ht.textContent = '';
      // Render activities for the day on the timeline and list
      timeline.renderActivities(data.activities);
      renderActivitiesList(filterActivitiesByDay(data.activities, currentDay));
    }

    function refreshAll(newData){
      data = newData || data;
      renderHeader(data.header, data);
      renderTotals(data.totals);
      // keep current day, re-render
      if (currentDay) {
        setDay(currentDay);
      }
    }

    // Load initial snapshot
    try {
      data = await fetchJSON(url);
    } catch (e) {
      console.error(e);
      return;
    }

    // Create timeline component
    const tlRoot = qs('#timeline');
    timeline = window.ServiceLogTimeline && window.ServiceLogTimeline.create(tlRoot, {
      initialDay: pickDefaultDay(data),
      mode: 'range',
      onHover: (info) => {
        const el = qs('#hover-time');
        if (!el) return;
        if (!info || !info.date) { el.textContent = ''; return; }
        try {
          const d = info.date instanceof Date ? info.date : new Date(info.date);
          const hh = String(d.getHours()).padStart(2, '0');
          const mm = String(d.getMinutes()).padStart(2, '0');
          el.textContent = `${hh}:${mm}`;
        } catch (e) {
          el.textContent = '';
        }
      },
      onSelect: async ({ start, end }) => {
        const statusEl = qs('#save-status');
        if (!selectedEvent) { statusEl.textContent = 'Selecciona un tipo de evento'; return; }
        statusEl.textContent = 'Guardando…';
        try {
          const payload = { event_type: selectedEvent, started_at: toIso(start) };
          if (end && (selectedEvent !== 'TRIP_START' && selectedEvent !== 'TRIP_END')) {
            payload.ended_at = toIso(end);
          }
          const notes = (qs('#notes').value || '').trim();
          if (notes) payload.notes = notes;

          const saveUrl = `${window.location.origin}/operations/service-logs/${logId}/events/`;
          const saved = await postJSON(saveUrl, payload);
          refreshAll(saved);
          statusEl.textContent = 'Guardado';
          setTimeout(() => statusEl.textContent = '', 1500);
        } catch (e) {
          statusEl.textContent = `Error: ${e.message}`;
        }
      }
    });

    // Initialize current day from timeline
    setDay(pickDefaultDay(data));

    // Event button handling (sets mode based on event type)
    qsa('.ev-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        qsa('.ev-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedEvent = btn.getAttribute('data-event');
        const isMarker = (selectedEvent === 'TRIP_START' || selectedEvent === 'TRIP_END');
        timeline.setMode(isMarker ? 'marker' : 'range');
      });
    });

    // Day navigation
    qs('#day-prev').addEventListener('click', () => {
      const d = new Date(currentDay.getTime());
      d.setDate(d.getDate() - 1);
      setDay(d);
    });
    qs('#day-next').addEventListener('click', () => {
      const d = new Date(currentDay.getTime());
      d.setDate(d.getDate() + 1);
      setDay(d);
    });

    // Initial header/totals render
    renderHeader(data.header, data);
    renderTotals(data.totals);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
