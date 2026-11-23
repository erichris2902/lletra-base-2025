(function(){
  function clamp(v, a, b){ return Math.max(a, Math.min(b, v)); }
  function minutesSinceMidnight(d){ return d.getHours()*60 + d.getMinutes(); }
  function atDayMinutes(day, minutes){
    const d = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 0, 0, 0, 0);
    d.setMinutes(minutes);
    return d;
  }
  function fmtDay(d){
    return d.toLocaleDateString(undefined, { weekday:'short', year:'numeric', month:'short', day:'numeric' });
  }
  function pctFromMinutes(min){ return (min/1440)*100; }

  const CAT_CLASS = {
    'DRIVING': 'sl-cat-driving',
    'PAUSE': 'sl-cat-pause',
    'AUXILIARY': 'sl-cat-aux',
    'EXCEPTION': 'sl-cat-exc',
    'REST': 'sl-cat-rest',
  };

  function createTimeline(rootEl, opts){
    const el = rootEl;
    el.classList.add('sl-timeline');

    // Selection overlay
    const sel = document.createElement('div');
    sel.className = 'sl-selection';
    sel.style.display = 'none';
    el.appendChild(sel);

    let currentDay = opts.initialDay || new Date();
    let mode = opts.mode || 'range'; // 'range' | 'marker'
    let pointerActive = false;
    let startSlot = null; // 0..48
    let endSlot = null;   // 0..48

    // Render activities for the visible day (with stacking lanes for overlaps)
    function renderActivities(activities){
      // clear old activity nodes
      Array.from(el.querySelectorAll('.sl-activity')).forEach(n=>n.remove());
      if (!activities || !activities.length){
        // Reset to base height and selection overlay
        el.style.height = '';
        sel.style.height = '';
        return;
      }

      // Build day-clipped segments for current day
      const dayStart = new Date(currentDay.getFullYear(), currentDay.getMonth(), currentDay.getDate(), 0,0,0,0);
      const dayEnd = new Date(dayStart.getTime());
      dayEnd.setDate(dayEnd.getDate()+1);

      const segs = [];
      for (const a of activities){
        try {
          const s = new Date(a.started_at);
          const e = new Date(a.ended_at);
          // Skip invalid
          if (!(s instanceof Date) || !(e instanceof Date) || isNaN(s) || isNaN(e)) continue;
          if (e <= dayStart || s >= dayEnd) continue; // outside day

          const startClamped = s < dayStart ? dayStart : s;
          const endClamped = e > dayEnd ? dayEnd : e;
          const startMin = minutesSinceMidnight(startClamped);
          const endMin = minutesSinceMidnight(endClamped);
          const duration = Math.max(0, endMin - startMin);
          if (duration <= 0) continue;

          segs.push({
            activity: a,
            startMin,
            endMin,
            duration,
          });
        } catch(e){ /* ignore bad rows */ }
      }

      // Assign lanes greedily to stack overlaps
      segs.sort((x,y)=> x.startMin - y.startMin || x.endMin - y.endMin);
      const laneEnds = []; // minutes end per lane
      const placed = [];
      for (const s of segs){
        let lane = 0;
        while (lane < laneEnds.length && s.startMin < laneEnds[lane]){
          lane++;
        }
        if (lane === laneEnds.length){ laneEnds.push(s.endMin); } else { laneEnds[lane] = s.endMin; }
        placed.push({ ...s, lane });
      }

      const maxLanes = Math.max(1, laneEnds.length);
      const baseTop = 24;           // px
      const blockH = 40;            // px (matches CSS)
      const gap = 4;                // px between lanes
      const totalHeight = baseTop + (blockH * maxLanes) + (gap * (maxLanes - 1)) + 8; // +bottom padding
      el.style.height = totalHeight + 'px';
      sel.style.top = '4px';
      sel.style.height = (totalHeight - 8) + 'px';

      // Render 
      for (const p of placed){
        const left = pctFromMinutes(p.startMin);
        const width = pctFromMinutes(p.duration);
        const div = document.createElement('div');
        div.className = 'sl-activity ' + (CAT_CLASS[p.activity.activity_type] || '');
        div.style.left = left + '%';
        div.style.width = width + '%';
        div.style.top = (baseTop + p.lane * (blockH + gap)) + 'px';
        const label = `${p.activity.activity_type}`;
        div.title = label;
        div.textContent = '';
        el.appendChild(div);
      }
    }

    function slotsFromEvent(ev){
      const rect = el.getBoundingClientRect();
      const x = clamp((ev.clientX || (ev.touches && ev.touches[0] && ev.touches[0].clientX) || 0) - rect.left, 0, rect.width);
      const ratio = rect.width > 0 ? x / rect.width : 0;
      const slot = Math.round(ratio * 48); // 0..48, snap to 30-min
      return clamp(slot, 0, 48);
    }

    function hideSelection(){ sel.style.display = 'none'; }
    function showSelection(a, b){
      const leftSlot = Math.min(a, b);
      const rightSlot = Math.max(a, b);
      const leftPct = (leftSlot/48)*100;
      const widthPct = ((rightSlot-leftSlot)/48)*100;
      sel.style.left = leftPct + '%';
      sel.style.width = widthPct + '%';
      sel.style.display = 'block';
    }

    function slotToDate(slot){
      const minutes = slot * 30; // 30-min blocks
      return atDayMinutes(currentDay, minutes);
    }

    function fireSelection(aSlot, bSlot){
      const start = slotToDate(aSlot);
      if (mode === 'marker'){
        opts.onSelect && opts.onSelect({ start: start, end: null, day: new Date(currentDay) });
      } else {
        const end = slotToDate(Math.max(aSlot+1, bSlot)); // ensure at least 30 minutes
        opts.onSelect && opts.onSelect({ start: start, end: end, day: new Date(currentDay) });
      }
    }

    function onPointerDown(ev){
      ev.preventDefault();
      pointerActive = true;
      startSlot = slotsFromEvent(ev);
      endSlot = startSlot;
      if (mode === 'marker'){
        // Show thin selection for feedback
        showSelection(startSlot, startSlot);
      } else {
        showSelection(startSlot, endSlot);
      }
    }

    function onPointerMove(ev){
      if (!pointerActive) return;
      endSlot = slotsFromEvent(ev);
      if (mode === 'marker'){
        showSelection(startSlot, startSlot);
      } else {
        showSelection(startSlot, endSlot);
      }
    }

    function onPointerUp(ev){
      if (!pointerActive) return;
      pointerActive = false;
      if (mode === 'marker'){
        fireSelection(startSlot, startSlot);
        hideSelection();
      } else {
        fireSelection(Math.min(startSlot, endSlot), Math.max(startSlot, endSlot));
        hideSelection();
      }
    }

    // Pointer/touch listeners
    el.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    // Hover indicator (mouse only; no-op on touch). Does not interfere with drag selection.
    function onHoverMove(ev){
      if (pointerActive) return; // don't emit hover while dragging
      const slot = slotsFromEvent(ev);
      if (opts && typeof opts.onHover === 'function') {
        const d = slotToDate(slot);
        opts.onHover({ date: d, slot: slot, minutes: slot*30 });
      }
    }
    function onHoverLeave(){
      if (opts && typeof opts.onHover === 'function') {
        opts.onHover(null);
      }
    }
    el.addEventListener('pointermove', onHoverMove);
    el.addEventListener('pointerleave', onHoverLeave);

    // Public API
    const api = {
      setMode: function(m){ mode = (m === 'marker') ? 'marker' : 'range'; },
      setDay: function(d){ currentDay = new Date(d.getFullYear(), d.getMonth(), d.getDate()); hideSelection(); },
      renderActivities: renderActivities,
      getDayLabel: function(){ return fmtDay(currentDay); },
    };

    return api;
  }

  // Expose globally
  window.ServiceLogTimeline = { create: createTimeline };
})();