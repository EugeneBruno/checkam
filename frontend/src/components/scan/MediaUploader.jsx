import { useRef } from 'react'

function MediaUploader({
  attachments,
  isCameraOpen,
  onCameraToggle,
  onFilesSelected,
  onRemove,
  onSampleVideo,
  recording,
  samplingId,
}) {
  const photoInputRef = useRef(null)
  const mediaInputRef = useRef(null)

  function handleSelection(event, source) {
    onFilesSelected(event.target.files, source)
    event.target.value = ''
  }

  return (
    <>
      <div className="capture-options">
        <button type="button" className="capture-option" onClick={() => {
          // Phones/tablets open the native camera; on a laptop that input only opens a file picker,
          // so open the live camera instead and use its "Take photo" button.
          const touch = navigator.maxTouchPoints > 0 && /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)
          if (touch) photoInputRef.current?.click()
          else if (!isCameraOpen) onCameraToggle()
        }}>
          <span className="option-icon photo-icon"><span aria-hidden="true">▧</span></span>
          <span><strong>Take a photo</strong><small>Open your device camera</small></span>
          <span className="icon option-arrow" aria-hidden="true">↗</span>
        </button>
        <button type="button" className="capture-option" onClick={() => mediaInputRef.current?.click()}>
          <span className="option-icon upload-icon"><span aria-hidden="true">↑</span></span>
          <span><strong>Choose multiple files</strong><small>Photos and 5–15 sec videos</small></span>
          <span className="icon option-arrow" aria-hidden="true">↗</span>
        </button>
        <button type="button" className="capture-option" onClick={onCameraToggle} disabled={recording}>
          <span className="option-icon stream-icon"><span aria-hidden="true">{isCameraOpen ? '■' : '◉'}</span></span>
          <span><strong>{isCameraOpen ? 'Close live camera' : 'Open live camera'}</strong><small>Take photos or record a 5–15 sec clip</small></span>
          <span className="icon option-arrow" aria-hidden="true">↗</span>
        </button>
      </div>
      <input
        ref={photoInputRef}
        className="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => handleSelection(event, 'photo capture')}
      />
      <input
        ref={mediaInputRef}
        className="visually-hidden"
        type="file"
        accept="image/*,video/*"
        multiple
        onChange={(event) => handleSelection(event, 'upload')}
      />

      <div className="attachment-heading">
        <h3>Added media <span>{attachments.length}</span></h3>
        <span>Previews stay on this device</span>
      </div>
      {attachments.length
        ? <ul className="attachment-grid">
          {attachments.map((item) => (
            <li className="attachment-card" key={item.id}>
              <div className="attachment-preview">
                {item.file.type.startsWith('image/')
                  ? <img src={item.url} alt={`Preview of ${item.file.name}`} />
                  : <video src={item.url} muted playsInline preload="metadata" aria-label={`Video preview of ${item.file.name}`} />}
                <button type="button" className="attachment-dismiss" aria-label={`Remove ${item.file.name}`} onClick={() => onRemove(item.id)}>×</button>
                {item.file.type.startsWith('video/') && <span className="attachment-video-label">VIDEO</span>}
              </div>
              <div className="attachment-card-info">
                <strong title={item.file.name}>{item.file.name}</strong>
                <small>{item.source} · {formatBytes(item.file.size)}</small>
              </div>
              {item.file.type.startsWith('video/') && <button type="button" className="sample-button" disabled={samplingId === item.id} onClick={() => onSampleVideo(item)}>{samplingId === item.id ? 'Sampling…' : 'Sample frames'}</button>}
            </li>
          ))}
        </ul>
        : <div className="empty-attachments">Media you add will appear here.</div>}
    </>
  )
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default MediaUploader