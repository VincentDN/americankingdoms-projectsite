/* Background music player, shared by the world atlas and its submap pages.
   Muted (volume 0) until the visitor raises the slider or presses play --
   nothing is fetched until that first gesture, since <audio preload="none">
   only starts downloading once playback is requested. */
(() => {
  'use strict';
  const TRACKS = [
    { src: '/medieval-america-map/assets/music/medieval-escape.mp3', title: 'Medieval Escape' },
    { src: '/medieval-america-map/assets/music/celtic-medieval.mp3', title: 'Irish Celtic Medieval' },
    { src: '/medieval-america-map/assets/music/kiravale-medieval.mp3', title: 'Kiravale Medieval' },
  ];
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

  let queue = [];
  let queueIndex = 0;
  let lastTrack = -1;

  function refillQueue() {
    queue = shuffle(TRACKS.map((_, i) => i));
    if (queue.length > 1 && queue[0] === lastTrack) [queue[0], queue[1]] = [queue[1], queue[0]];
    queueIndex = 0;
  }

  function loadCurrent() {
    if (queueIndex >= queue.length) refillQueue();
    const idx = queue[queueIndex];
    lastTrack = idx;
    const track = TRACKS[idx];
    audio.src = track.src;
    if (trackLabel) trackLabel.textContent = track.title;
  }

  refillQueue();
  loadCurrent();

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

  audio.volume = 0;
  if (volume) volume.value = 0;

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
})();
