/* Background music player, shared by the world atlas and its submap pages.
   Plays on load at a low volume, and carries its shuffle queue, current
   track position and volume across page navigations (world atlas <-> a
   county page, say) via sessionStorage -- these are separate full page
   loads, not an SPA, so without this every navigation would restart the
   player from track one. Browsers only allow audio with sound to autoplay
   after the visitor has already interacted with the site (or its
   engagement heuristics allow it, which they increasingly do once a
   visitor has played audio with sound here before), so this attempts
   play() right away and, if that's blocked, starts on the visitor's first
   click, tap or keypress anywhere on the page instead -- silent until
   then, never muted autoplay dressed up as playing. */
(() => {
  'use strict';
  const TRACKS = [
    { src: '/medieval-america-map/assets/music/medieval-escape.mp3', title: 'Medieval Escape' },
    { src: '/medieval-america-map/assets/music/celtic-medieval.mp3', title: 'Irish Celtic Medieval' },
    { src: '/medieval-america-map/assets/music/kiravale-medieval.mp3', title: 'Kiravale Medieval' },
  ];
  const STORAGE_KEY = 'ak-music-state';
  const $ = id => document.getElementById(id);
  const audio = $('music-audio');
  const toggleBtn = $('music-toggle');
  const popover = $('music-popover');
  const playBtn = $('music-playpause');
  const volume = $('music-volume');
  const trackLabel = $('music-track');
  if (!audio || !toggleBtn) return;

  const shuffle = arr => {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  const readSaved = () => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
      if (!saved || !Array.isArray(saved.queue) || saved.queue.length !== TRACKS.length) return null;
      if (!saved.queue.every(i => Number.isInteger(i) && i >= 0 && i < TRACKS.length)) return null;
      if (!Number.isInteger(saved.queueIndex) || saved.queueIndex < 0 || saved.queueIndex >= saved.queue.length) return null;
      return saved;
    } catch { return null; }
  };
  const writeSaved = () => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        queue, queueIndex, currentTime: audio.currentTime,
        volume: audio.volume, playing: !audio.paused,
      }));
    } catch { /* private browsing or storage disabled: continuity is best-effort */ }
  };

  let queue = [];
  let queueIndex = 0;
  let lastTrack = -1;

  function refillQueue() {
    queue = shuffle(TRACKS.map((_, i) => i));
    if (queue.length > 1 && queue[0] === lastTrack) [queue[0], queue[1]] = [queue[1], queue[0]];
    queueIndex = 0;
  }

  function loadCurrent(resumeAt) {
    if (queueIndex >= queue.length) refillQueue();
    const idx = queue[queueIndex];
    lastTrack = idx;
    const track = TRACKS[idx];
    audio.src = track.src;
    if (trackLabel) trackLabel.textContent = track.title;
    if (resumeAt) {
      // preload="none" otherwise waits for an explicit play() before
      // fetching, and play() itself may be deferred (autoplay blocked
      // until the visitor's first interaction) -- load() is always
      // allowed and needed here regardless, to resume mid-track.
      audio.addEventListener('loadedmetadata', () => { audio.currentTime = resumeAt; }, { once: true });
      audio.load();
    }
  }

  const saved = readSaved();
  const DEFAULT_VOLUME = 0.18;
  if (saved) {
    queue = saved.queue;
    queueIndex = saved.queueIndex;
    lastTrack = queue[queueIndex];
    loadCurrent(saved.currentTime);
    audio.volume = typeof saved.volume === 'number' ? saved.volume : DEFAULT_VOLUME;
  } else {
    refillQueue();
    loadCurrent();
    audio.volume = DEFAULT_VOLUME;
  }
  if (volume) volume.value = Math.round(audio.volume * 100);

  audio.addEventListener('ended', () => {
    queueIndex++;
    loadCurrent();
    audio.play().catch(() => {});
  });

  let open = false;
  const setOpen = v => {
    open = v;
    popover.hidden = !open;
    toggleBtn.setAttribute('aria-expanded', String(open));
  };
  toggleBtn.addEventListener('click', () => setOpen(!open));
  document.addEventListener('click', e => {
    if (open && e.target !== toggleBtn && !popover.contains(e.target)) setOpen(false);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && open) { setOpen(false); toggleBtn.focus(); }
  });

  const updatePlayButton = () => {
    if (!playBtn) return;
    playBtn.textContent = audio.paused ? '▶' : '⏸';
    playBtn.setAttribute('aria-label', audio.paused ? 'Play music' : 'Pause music');
  };
  updatePlayButton();
  audio.addEventListener('play', updatePlayButton);
  audio.addEventListener('pause', updatePlayButton);

  if (playBtn) playBtn.addEventListener('click', () => {
    if (audio.paused) audio.play().catch(() => {});
    else audio.pause();
  });

  if (volume) volume.addEventListener('input', () => {
    audio.volume = Number(volume.value) / 100;
  });

  // Best-effort autoplay: most browsers refuse this on a cold load, in
  // which case fall back to the visitor's first interaction anywhere on
  // the page (not just the player itself). A page reached with saved
  // state that had playback paused stays paused.
  const startOnFirstInteraction = () => {
    audio.play().catch(() => {});
    ['pointerdown', 'keydown'].forEach(type => document.removeEventListener(type, startOnFirstInteraction));
  };
  if (!saved || saved.playing) {
    audio.play().catch(() => {
      ['pointerdown', 'keydown'].forEach(type => document.addEventListener(type, startOnFirstInteraction, { once: true }));
    });
  }

  // Persist across the page navigation that's about to happen (or the tab
  // closing): pagehide is the reliable one for both, plus periodic saves
  // as a safety net and immediate ones on state changes a visitor might
  // make right before navigating away.
  window.addEventListener('pagehide', writeSaved);
  document.addEventListener('visibilitychange', () => { if (document.hidden) writeSaved(); });
  audio.addEventListener('pause', writeSaved);
  audio.addEventListener('volumechange', writeSaved);
  setInterval(() => { if (!audio.paused) writeSaved(); }, 5000);
})();
