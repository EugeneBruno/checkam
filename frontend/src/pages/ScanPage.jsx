import { useEffect, useRef, useState } from 'react'
import ManualInputForm from '../components/scan/ManualInputForm.jsx.jsx'
import MediaUploader from '../components/scan/MediaUploader.jsx'
import SituationToggle from '../components/scan/SituationToggle.jsx'
import VideoRecorder from '../components/scan/VideoRecorder.jsx'
import checkAmLogo from '../public/Check_Am_Logo-removebg-preview.png'

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`

function readVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      const duration = video.duration
      video.removeAttribute('src')
      video.load()
      URL.revokeObjectURL(url)
      resolve(duration)
    }
    video.onerror = () => {
      video.removeAttribute('src')
      video.load()
      URL.revokeObjectURL(url)
      reject(new Error(`Could not read the duration of ${file.name}.`))
    }
    video.src = url
  })
}

function Icon({ children, className = '' }) {
  return <span className={`icon ${className}`} aria-hidden="true">{children}</span>
}

function ScanPage({ isActive = true, onBack, onStartResearch, initialProduct = null }) {
  const [attachments, setAttachments] = useState([])
  const [productDetails, setProductDetails] = useState(initialProduct || {})
  const [stream, setStream] = useState(null)
  const [recording, setRecording] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [samplingId, setSamplingId] = useState('')
  const [situationIntent, setSituationIntent] = useState('BEFORE_BUYING')
  const [urgency, setUrgency] = useState('routine')
  const [safeToApproach, setSafeToApproach] = useState('')
  const [prepared, setPrepared] = useState(false)
  const videoRef = useRef(null)
  const attachmentUrlsRef = useRef(new Set())
  const summaryRef = useRef(null)
  const locationRef = useRef(null)
  const peopleRef = useRef(null)
  const detailsRef = useRef(null)

  useEffect(() => {
    if (videoRef.current && stream) videoRef.current.srcObject = stream
  }, [stream])

  useEffect(() => () => {
    stream?.getTracks().forEach((track) => track.stop())
  }, [stream])

  useEffect(() => {
    if (isActive) return
    stream?.getTracks().forEach((track) => track.stop())
  }, [isActive, stream])

  useEffect(() => () => {
    attachmentUrlsRef.current.forEach((url) => URL.revokeObjectURL(url))
  }, [])

  async function addFiles(fileList, source = 'upload', validateVideoDuration = true) {
    const selectedFiles = [...fileList]
    const validFiles = selectedFiles.filter((file) =>
      file.type.startsWith('image/') || file.type.startsWith('video/'),
    )
    if (!validFiles.length) {
      if (selectedFiles.length) setCameraError('Choose an image or video file.')
      return
    }

    const acceptedFiles = []
    const rejectedFiles = selectedFiles.length > validFiles.length
      ? ['Some files were skipped because they are not images or videos.']
      : []
    for (const file of validFiles) {
      if (validateVideoDuration && file.type.startsWith('video/')) {
        try {
          const duration = await readVideoDuration(file)
          if (duration < 5 || duration > 15) {
            rejectedFiles.push(`${file.name} must be 5–15 seconds long.`)
            continue
          }
        } catch (error) {
          rejectedFiles.push(error.message)
          continue
        }
      }
      acceptedFiles.push(file)
    }

    if (rejectedFiles.length) setCameraError(rejectedFiles.join(' '))
    else setCameraError('')
    if (!acceptedFiles.length) return

    const newAttachments = acceptedFiles.map((file) => {
      const url = URL.createObjectURL(file)
      attachmentUrlsRef.current.add(url)
      return { id: makeId(), file, source, url }
    })
    setAttachments((current) => [...current, ...newAttachments])
    setPrepared(false)
    // Check Am reads photos, so pull a few frames out of each video straight away
    newAttachments.filter((item) => item.file.type.startsWith('video/')).forEach((item) => sampleVideo(item))
  }

  function removeAttachment(id) {
    const removed = attachments.find((item) => item.id === id)
    if (removed) {
      URL.revokeObjectURL(removed.url)
      attachmentUrlsRef.current.delete(removed.url)
    }
    setAttachments((current) => current.filter((item) => item.id !== id))
  }

  async function startCamera() {
    setCameraError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Live camera capture is not available in this browser. Try HTTPS or choose a file instead.')
      return
    }

    try {
      const cameraStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      })
      setStream(cameraStream)
    } catch (error) {
      setCameraError(error.name === 'NotAllowedError'
        ? 'Camera access was blocked. Allow camera access in your browser settings, or choose a file instead.'
        : 'Could not start the camera. Check that it is connected and not in use by another app.')
    }
  }

  function stopCamera() {
    stream?.getTracks().forEach((track) => track.stop())
    setStream(null)
  }

  function captureFrame() {
    const video = videoRef.current
    if (!video?.videoWidth || !video.videoHeight) {
      setCameraError('The camera is still starting. Try again in a moment.')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      if (blob) addFiles([new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' })], 'camera')
    }, 'image/jpeg', 0.9)
  }

  async function sampleVideo(item) {
    setSamplingId(item.id)
    setCameraError('')
    const video = document.createElement('video')
    const videoUrl = URL.createObjectURL(item.file)
    video.preload = 'metadata'
    video.muted = true
    video.playsInline = true
    video.src = videoUrl

    try {
      await new Promise((resolve, reject) => {
        video.onloadedmetadata = resolve
        video.onerror = () => reject(new Error('Could not read this video.'))
      })
      if (!Number.isFinite(video.duration) || video.duration <= 0) throw new Error('This video has no readable duration.')
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        await new Promise((resolve, reject) => {
          video.onloadeddata = resolve
          video.onerror = () => reject(new Error('Could not decode this video.'))
        })
      }

      const count = Math.min(5, Math.max(1, Math.ceil(video.duration / 4)))
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      for (let index = 0; index < count; index += 1) {
        if (index > 0) {
          const seekComplete = new Promise((resolve, reject) => {
            video.onseeked = resolve
            video.onerror = () => reject(new Error('Could not sample a frame from this video.'))
          })
          video.currentTime = (video.duration - 0.1) * index / (count - 1)
          await seekComplete
        }
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88))
        if (!blob) throw new Error('Could not create a frame from this video.')
        const frame = new File([blob], `${item.file.name}-frame-${index + 1}.jpg`, { type: 'image/jpeg' })
        addFiles([frame], 'video frame')
      }
    } catch (error) {
      setCameraError(error.message)
    } finally {
      video.removeAttribute('src')
      video.load()
      URL.revokeObjectURL(videoUrl)
      setSamplingId('')
    }
  }

  function prepareIntake(event) {
    event.preventDefault()
    const hasPhoto = attachments.some(({ file }) => file.type.startsWith('image/'))
    const hasDetails = Object.values(productDetails).some((value) => String(value || '').trim())
    if (!hasPhoto && !hasDetails) {
      setCameraError('Add a photo of the product, or type at least one detail (name, NAFDAC number, barcode or IMEI).')
      return
    }
    startResearch()
  }

  function downloadManifest() {
    const manifest = {
      createdAt: new Date().toISOString(),
      product: productDetails,
      situation: {
        intent: situationIntent,
        summary: (summaryRef.current?.value || "").trim(),
        location: (locationRef.current?.value || "").trim(),
        urgency,
        peopleInvolved: (peopleRef.current?.value || "").trim(),
        safeToApproach,
        additionalDetails: (detailsRef.current?.value || "").trim(),
      },
      attachments: attachments.map(({ file, source }) => ({
        name: file.name,
        type: file.type,
        sizeBytes: file.size,
        source,
      })),
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'checkam-intake-manifest.json'
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  function startResearch() {
    if (recording) {
      setCameraError('Finish recording your video before opening the research trace.')
      return
    }
    if (stream) stopCamera()
    onStartResearch({
      product: productDetails,
      situation: {
        intent: situationIntent,
        summary: (summaryRef.current?.value || "").trim(),
        location: (locationRef.current?.value || "").trim(),
        urgency,
        peopleInvolved: (peopleRef.current?.value || "").trim(),
        safeToApproach,
        additionalDetails: (detailsRef.current?.value || "").trim(),
      },
      attachments: attachments.map(({ file, source }) => ({
        name: file.name,
        type: file.type,
        sizeBytes: file.size,
        source,
      })),
      // the real files: App keeps them in memory and CheckingPage sends them to Check Am
      files: attachments.map(({ file }) => file).filter((file) => file.type.startsWith('image/')),
    })
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CheckAm home" onClick={(event) => {
          if (onBack) {
            event.preventDefault()
            onBack()
          }
        }}>
          <img
            src={checkAmLogo}
            alt="CheckAm"
           className="absolute left-0 -top-4 h-auto w-40 max-w-none"
          />
        </a>
        <div className="topbar-status ml-16" ><span className="status-dot" /> New check</div>
        <span className="privacy-note"><Icon>◈</Icon> Photos are only sent when you press Check</span>
      </header>

      <div className="page">
        <div className="page-heading">
          <div>
            <div className="eyebrow"><span>01</span> NEW CHECK</div>
            <h1>Check a <span>product.</span></h1>
            <p className="intro">Photograph the front, the NAFDAC number, the batch and expiry, and the barcode. Or type what you can read.</p>
          </div>
          <div className="step-pill"><span className="step-active">1</span> Photos <i /> <span>2</span> Result</div>
        </div>

        <form className="intake-grid" onSubmit={prepareIntake}>
          <section className="panel capture-panel" aria-labelledby="capture-heading">
            <div className="panel-heading">
              <div className="section-index">A</div>
              <div><h2 id="capture-heading">Photos of the product</h2><p>Front, NAFDAC number, batch and expiry, barcode. More photos help.</p></div>
            </div>

            <div className={`camera-view ${stream ? 'camera-live' : ''}`}>
              {stream
                ? <>
                  <video ref={videoRef} autoPlay muted playsInline aria-label="Live camera preview" />
                  <VideoRecorder
                    isActive={isActive}
                    stream={stream}
                    onCaptureFrame={captureFrame}
                    onError={setCameraError}
                    onRecordingChange={setRecording}
                    onVideoRecorded={(file) => addFiles([file], 'recording', false)}
                  />
                </>
                : <div className="camera-placeholder">
                  <div className="camera-orbit"><Icon>◉</Icon></div>
                  <strong>Photograph the pack</strong>
                  <span>Use your camera or upload photos. Phones: hold steady and fill the frame with the label.</span>
                </div>}
            </div>
            {cameraError && <p className="inline-error" role="alert">{cameraError}</p>}
            <MediaUploader
              attachments={attachments}
              isCameraOpen={Boolean(stream)}
              onCameraToggle={stream ? stopCamera : startCamera}
              onFilesSelected={addFiles}
              onRemove={removeAttachment}
              onSampleVideo={sampleVideo}
              recording={recording}
              samplingId={samplingId}
            />
            {initialProduct && <p className="manual-input-note"><strong>Checking {(initialProduct.productName && initialProduct.brand && initialProduct.productName.toLowerCase().startsWith(initialProduct.brand.toLowerCase()) ? initialProduct.productName : [initialProduct.brand, initialProduct.productName].filter(Boolean).join(' ')) || 'the same product'} again.</strong> Add the photo the result asked for; your earlier details are filled in below.</p>}
            <ManualInputForm
              open={Boolean(initialProduct)}
              values={productDetails}
              onChange={(nextValues) => {
                setProductDetails(nextValues)
                setPrepared(false)
              }}
            />
          </section>

          <section className="panel context-panel" aria-labelledby="context-heading">
            <div className="panel-heading">
              <div className="section-index">B</div>
              <div><h2 id="context-heading">About this check</h2><p>This shapes the advice you get.</p></div>
            </div>

            <SituationToggle
              value={situationIntent}
              onChange={(value) => {
                setSituationIntent(value)
                setPrepared(false)
              }}
            />

            <label className="field-label" htmlFor="situation-summary">Notes <span>Optional</span></label>
            <textarea ref={summaryRef} id="situation-summary" rows="3" maxLength="600" placeholder="Anything that looked wrong: price, seal, print, seller…" onChange={() => setPrepared(false)} />
            <div className="field">
              <label className="field-label" htmlFor="location">Where did you see it? <span>Optional</span></label>
              <input ref={locationRef} id="location" type="text" maxLength="160" placeholder="Market, shop or state, e.g. Idumota, Lagos" onChange={() => setPrepared(false)} />
            </div>

            <div className="privacy-card"><Icon>◈</Icon><p><strong>What happens next</strong><br />Your photos and details are sent to Check Am, which reads the pack and checks it against NAFDAC, SON and NCC data, alerts and other buyers’ scans. Videos are turned into a few photos automatically.</p></div>
            <button type="submit" className="button button-primary">Check this product <span>→</span></button>

            {prepared && <div className="prepared-card" role="status">
              <strong>Intake ready to review</strong>
              <p>{attachments.length} attachment{attachments.length === 1 ? '' : 's'} · {urgency === 'urgent' ? 'Urgent' : urgency === 'soon' ? 'Needs attention' : 'Routine'} · Local preview only</p>
              <button type="button" onClick={downloadManifest}>Download details manifest</button>
              <small>The manifest contains details and file names—not the media files.</small>
              <button type="button" className="prepared-start" onClick={startResearch}>View research trace <span>→</span></button>
              <small>The trace is a demo until an agent service is connected.</small>
            </div>}
          </section>
        </form>

        <footer className="page-footer"><span>Check Am</span><span>Evidence, not a guarantee.</span></footer>
      </div>
    </main>
  )
}

export default ScanPage