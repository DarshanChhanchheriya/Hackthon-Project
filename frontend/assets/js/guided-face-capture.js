// Guided, fully-automatic 5-pose face enrollment capture. Shows an oval
// face guide + a rotating instruction ("Look straight", "Turn slightly
// left"...) with a visible countdown, then auto-captures each pose —
// no button clicks needed during the sequence itself.
window.GuidedFaceCapture = (() => {
  const POSES = [
    "Look straight at the camera",
    "Turn your head slightly left",
    "Turn your head slightly right",
    "Tilt your chin up a little",
    "Tilt your chin down a little",
  ];
  const HOLD_SECONDS = 3;

  function captureFrame(video, canvas) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.9);
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  /**
   * @param {Object} opts
   * @param {HTMLVideoElement} opts.video
   * @param {HTMLCanvasElement} opts.canvas
   * @param {HTMLElement} opts.instructionEl - shows the current pose prompt
   * @param {HTMLElement} opts.countdownEl - shows the "3 2 1" countdown
   * @param {HTMLElement[]} opts.dotEls - 5 progress-dot elements
   * @param {(dataUrl:string, index:number)=>void} [opts.onCapture] - fired after each pose is captured
   * @param {()=>boolean} [opts.isCancelled] - polled between steps; abort if it returns true
   * @returns {Promise<string[]>} the 5 captured frames
   */
  async function run({ video, canvas, instructionEl, countdownEl, dotEls, onCapture, isCancelled }) {
    const captures = [];
    for (let i = 0; i < POSES.length; i++) {
      if (isCancelled?.()) break;
      instructionEl.textContent = POSES[i];
      for (let s = HOLD_SECONDS; s > 0; s--) {
        if (isCancelled?.()) return captures;
        countdownEl.textContent = s;
        await sleep(1000);
      }
      countdownEl.textContent = "📸";
      const frame = captureFrame(video, canvas);
      captures.push(frame);
      if (dotEls[i]) dotEls[i].style.background = "var(--accent)";
      onCapture?.(frame, i);
      await sleep(500);
    }
    countdownEl.textContent = "";
    instructionEl.textContent = "All set!";
    return captures;
  }

  return { run, POSES };
})();
