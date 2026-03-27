import React, { useState, useRef, useCallback } from 'react';
import { FiUploadCloud, FiX, FiFile, FiImage, FiVideo, FiMusic } from 'react-icons/fi';

function FileUploader({ files, setFiles, accept }) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const getFileIcon = (fileName) => {
    const ext = fileName.split('.').pop().toLowerCase();
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'];
    const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'];
    const audioExts = ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'];

    if (imageExts.includes(ext)) return <FiImage size={14} />;
    if (videoExts.includes(ext)) return <FiVideo size={14} />;
    if (audioExts.includes(ext)) return <FiMusic size={14} />;
    return <FiFile size={14} />;
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  }, [setFiles]);

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selected]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-zone-icon">
          <FiUploadCloud />
        </div>
        <p className="upload-zone-text">
          Drop files here or <strong>click to browse</strong>
        </p>
        <p className="upload-zone-hint">
          Supports images, videos, and audio files (max 50MB)
        </p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={accept || 'image/*,video/*,audio/*'}
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {files.length > 0 && (
        <div className="file-tags">
          {files.map((file, index) => (
            <div key={index} className="file-tag">
              {getFileIcon(file.name)}
              <span>{file.name}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                ({formatSize(file.size)})
              </span>
              <button
                className="file-tag-remove"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
              >
                <FiX size={10} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FileUploader;
