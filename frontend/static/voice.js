/* One capture session per page. Recorded audio stays in browser memory for replay. */
(() => {
  let session = null;
  let playbackUrl = null;
  const el = id => document.getElementById(id);
  function label(button, text) {
    const content = button.querySelector('.q-btn__content');
    (content || button).textContent = text;
    button.setAttribute('aria-label', text);
  }
  function release(s) {
    cancelAnimationFrame(s.frame);
    s.stream?.getTracks().forEach(track => track.stop());
    s.context?.close().catch(() => {});
    s.bars.forEach(bar => { bar.style.height = '6px'; });
  }
  function clearPlayback() {
    const audio = el('voice-audio');
    const button = el('voice-playback');
    if (audio) {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    }
    if (button) {
      button.hidden = true;
      label(button, '播放剛才錄音');
    }
    if (playbackUrl) URL.revokeObjectURL(playbackUrl);
    playbackUrl = null;
  }
  function keepForPlayback(blob) {
    clearPlayback();
    const audio = el('voice-audio');
    const button = el('voice-playback');
    if (!audio || !button) return;
    playbackUrl = URL.createObjectURL(blob);
    audio.src = playbackUrl;
    audio.load();
    audio.onended = () => label(button, '播放剛才錄音');
    button.hidden = false;
  }
  async function play() {
    const audio = el('voice-audio');
    const button = el('voice-playback');
    const status = el('voice-status');
    if (!audio?.src || !button) return;
    if (!audio.paused) {
      audio.pause();
      label(button, '播放剛才錄音');
      if (status) status.textContent = '已停止播放';
      return;
    }
    if (audio.ended) audio.currentTime = 0;
    try {
      await audio.play();
      label(button, '停止播放');
      if (status) status.textContent = '正在播放剛才的錄音';
    } catch (_) {
      label(button, '播放剛才錄音');
      if (status) status.textContent = '無法播放錄音，請再錄一次。';
    }
  }
  function cancel() {
    const s = session;
    if (s) {
      s.cancelled = true;
      s.abort.abort();
      if (s.recorder?.state === 'recording') s.recorder.stop();
      release(s);
      session = null;
    }
    clearPlayback();
  }
  function finish(s, message) {
    if (s.cancelled || session !== s) return;
    release(s);
    s.status.textContent = message;
    s.button.disabled = false;
    label(s.button, '開始錄音');
    session = null;
  }
  async function upload(s) {
    release(s);
    if (s.cancelled) return;
    s.phase = 'transcribing';
    s.button.disabled = true;
    label(s.button, '轉成文字中');
    s.status.textContent = '正在轉成文字…';
    const blob = new Blob(s.chunks, {type: s.recorder.mimeType});
    if (!blob.size) { finish(s, '沒有收到錄音，請再錄一次。'); return; }
    keepForPlayback(blob);
    const form = new FormData();
    const extension = s.recorder.mimeType.includes('mp4') ? 'm4a' : 'webm';
    form.append('audio', blob, `recording.${extension}`);
    const timeout = setTimeout(() => s.abort.abort(), 180000);
    try {
      const response = await fetch('/api/transcribe', {
        method: 'POST', body: form, signal: s.abort.signal,
      });
      if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('語音服務回應異常，請稍後再試。');
      }
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string'
        ? result.detail : '語音轉文字失敗，請再試一次。');
      if (s.cancelled) return;
      const text = String(result.text || '').trim();
      s.result.textContent = text;
      s.result.hidden = !text;
      // Explicit NiceGUI event bridges the transcription into Python search state.
      s.root.dispatchEvent(new CustomEvent('voice-result', {detail: {text}}));
      finish(s, text ? '請確認文字，再找教學。' : '沒有聽到說話，請再錄一次。');
    } catch (error) {
      if (!s.cancelled) finish(s, error.name === 'AbortError'
        ? '轉換等待太久，請再試一次。' : error.message);
    } finally { clearTimeout(timeout); }
  }
  async function toggle() {
    if (session) {
      if (session.phase === 'recording') {
        session.phase = 'stopping';
        session.button.disabled = true;
        session.recorder.stop();
      }
      return;
    }
    const root = el('voice-page');
    if (!root) return;
    clearPlayback();
    const s = {
      root, button: el('voice-start'), status: el('voice-status'),
      result: el('voice-transcript'), bars: [...el('voice-wave').children],
      phase: 'permission', chunks: [], abort: new AbortController(), cancelled: false,
    };
    session = s;
    s.button.disabled = true;
    s.result.hidden = true;
    s.root.dispatchEvent(new CustomEvent('voice-result', {detail: {text: ''}}));
    s.status.textContent = '請允許使用麥克風';
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error('此頁無法錄音，請使用 localhost 或 HTTPS 開啟。');
      }
      // Permission request runs directly in the click handler, before any network call.
      const pendingStream = navigator.mediaDevices.getUserMedia({audio: true});
      const Context = window.AudioContext || window.webkitAudioContext;
      if (Context) {
        try { s.context = new Context(); s.context.resume().catch(() => {}); } catch (_) {}
      }
      s.stream = await pendingStream;
      if (s.cancelled) { release(s); return; }
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm']
        .find(type => MediaRecorder.isTypeSupported(type));
      s.recorder = new MediaRecorder(s.stream, mimeType ? {mimeType} : {});
      s.recorder.ondataavailable = event => { if (event.data.size) s.chunks.push(event.data); };
      s.recorder.onstop = () => {
        if (s.failed) return;
        upload(s);
      };
      s.recorder.onerror = () => {
        s.failed = true;
        finish(s, '錄音中斷，請再錄一次。');
      };
      if (s.context) {
        try {
          s.analyser = s.context.createAnalyser();
          s.analyser.fftSize = 256;
          s.context.createMediaStreamSource(s.stream).connect(s.analyser);
        } catch (_) { s.analyser = null; }
      }
      s.recorder.start(250);
      s.phase = 'recording';
      label(s.button, '結束錄音');
      s.button.disabled = false;
      s.status.textContent = '正在錄音，再按一次結束';
      const samples = new Uint8Array(256);
      function meter() {
        if (s.cancelled || s.phase !== 'recording') return;
        if (s.analyser) {
          s.analyser.getByteTimeDomainData(samples);
          let energy = 0;
          for (const value of samples) energy += ((value - 128) / 128) ** 2;
          const level = Math.min(1, Math.sqrt(energy / samples.length) * 8);
          s.bars.forEach((bar, i) => {
            bar.style.height = `${6 + level * (24 + (i % 5) * 5)}px`;
          });
        }
        s.frame = requestAnimationFrame(meter);
      }
      meter();
    } catch (error) {
      const messages = {
        NotAllowedError: '請允許麥克風後再按一次。',
        NotFoundError: '找不到麥克風，請接上麥克風。',
        NotReadableError: '麥克風無法使用，請關閉其他錄音程式再試。',
      };
      finish(s, messages[error.name] || error.message || '無法開始錄音，請再試一次。');
    }
  }
  // Cancel on navigation/removal, including while a permission prompt is pending.
  new MutationObserver(() => {
    if ((session && !session.root.isConnected) || (playbackUrl && !el('voice-page'))) cancel();
  })
    .observe(document.documentElement, {childList: true, subtree: true});
  window.addEventListener('pagehide', cancel);
  window.ElderVoice = {toggle, cancel, play};
})();
