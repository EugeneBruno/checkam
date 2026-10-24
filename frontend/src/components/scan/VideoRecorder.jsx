import { useEffect, useRef, useState } from 'react'

const MIN_DURATION_MS = 5000
const MAX_DURATION_MS = 15000

function VideoRecorder({ isActive, stream, onCaptureFrame, onError, onRecordingChange, onVideoRecorded }) {
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const startedAtRef = useRef(0)
  const timerRef = useRef(null)
  const discardRef = useRef(false)

  useEffect(() => {
    if (!isActive && recorderRef.current?.state === 'recording') {
      discardRef.current = true
      window.clearInterval(timerRef.current)
      recorderRef.current.stop()
    }

    return () => {
      window.clearInterval(timerRef.current)
      const recorder = recorderRef.current
      if (recorder?.state === 'recording') {
        discardRef.current = true
        recorder.stop()
      }
    }
  }, [isActive, stream])

  function startRecording() {
    if (!stream) {
      onError('Open the camera before recording a video.')
      return
    }
    if (!window.MediaRecorder) {
      onError('Video recording is not supported in this browser.')
      return
    }

    const mimeType = ['video/webm;codecs=vp9', 'video/webm', 'video/mp4']
      .find((type) => MediaRecorder.isTypeSupported(type))
    if (!mimeType) {
      onError('This browser does not support a compatible video format.')
      return
    }

    try {
      const recorder = new MediaRecorder(stream, { mimeType })
      recorderRef.current = recorder
      chunksRef.current = []
      discardRef.current = false
      startedAtRef.current = Date.now()
      setElapsed(0)

      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data)
      }
      recorder.onerror = () => {
        discardRef.current = true
        onError('The browser could not complete the video recording. Please try again.')
        if (recorder.state === 'recording') recorder.stop()
      }
      recorder.onstop = () => {
        window.clearInterval(timerRef.current)
        const duration = Date.now() - startedAtRef.current
        setRecording(false)
        onRecordingChange(false)
        setElapsed(Math.min(duration, MAX_DURATION_MS))
        recorderRef.current = null

        if (discardRef.current) {
          chunksRef.current = []
          return
        }
        if (duration < MIN_DURATION_MS) {
          chunksRef.current = []
          onError('The clip was shorter than 5 seconds and was discarded. Record for at least 5 seconds.')
          return
        }

        const extension = mimeType.includes('mp4') ? 'mp4' : 'webm'
        const clip = new File(chunksRef.current, `recording-${Date.now()}.${extension}`, { type: mimeType })
        chunksRef.current = []
        onVideoRecorded(clip)
      }

      recorder.start(500)
      setRecording(true)
      onRecordingChange(true)
      onError('')
      timerRef.current = window.setInterval(() => {
        const duration = Date.now() - startedAtRef.current
        setElapsed(Math.min(duration, MAX_DURATION_MS))
        if (duration >= MAX_DURATION_MS && recorder.state === 'recording') recorder.stop()
      }, 100)
    } catch {
      onError('Could not start video recording. Check camera permissions and try again.')
    }
  }

  function stopRecording() {
    const duration = Date.now() - startedAtRef.current
    if (duration < MIN_DURATION_MS) {
      onError(`Record for at least 5 seconds. ${Math.ceil((MIN_DURATION_MS - duration) / 1000)} seconds remaining.`)
      return
    }
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  const progress = Math.min(100, (elapsed / MAX_DURATION_MS) * 100)
  const remainingSeconds = Math.max(0, Math.ceil((MAX_DURATION_MS - elapsed) / 1000))

  return (
    <div className="video-recorder">
      {recording && <div className="recording-meter" role="status" aria-live="polite">
        <div className="recording-meter-copy">
          <strong><span className="recording-meter-dot" /> Recording clip</strong>
          <span>{(elapsed / 1000).toFixed(1)}s · auto-stop in {remainingSeconds}s</span>
        </div>
        <div className="recording-meter-track" role="progressbar" aria-label="Video recording duration" aria-valuemin="0" aria-valuemax="15" aria-valuenow={Math.floor(elapsed / 1000)}>
          <span style={{ width: `${progress}%` }} />
          <i className="recording-minimum-marker" />
        </div>
        <small>Minimum 5 seconds · maximum 15 seconds</small>
      </div>}
      <div className="camera-actions">
        <button type="button" className="button button-light" onClick={onCaptureFrame} disabled={recording}>
          <span aria-hidden="true">◎</span> Capture frame
        </button>
        {recording
          ? <button type="button" className="button button-recording" disabled={elapsed < MIN_DURATION_MS} onClick={stopRecording}>
            <span />{elapsed < MIN_DURATION_MS ? `Wait ${Math.ceil((MIN_DURATION_MS - elapsed) / 1000)}s` : 'Stop recording'}
          </button>
          : <button type="button" className="button button-record" onClick={startRecording}>
            <span /> Record 5–15 sec
          </button>}
      </div>
    </div>
  )
}

export default VideoRecorder