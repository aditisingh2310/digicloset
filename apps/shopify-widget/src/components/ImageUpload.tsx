import { useState } from 'react';
import './ImageUpload.css';

interface ImageUploadProps {
  onUpload: (userImage: string, garmentImage: string) => Promise<void>;
}

/**
 * ImageUpload Component
 * 
 * Handles:
 * - File input validation
 * - Image preview
 * - Drag and drop
 * - Error handling
 */
export default function ImageUpload({ onUpload }: ImageUploadProps) {
  const [userImage, setUserImage] = useState<string | null>(null);
  const [garmentImage, setGarmentImage] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  const validateImage = (file: File): string | null => {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!validTypes.includes(file.type)) {
      return 'Invalid file type. Use JPEG, PNG, or WebP';
    }

    if (file.size > maxSize) {
      return 'File too large. Max 10MB';
    }

    return null;
  };

  const handleFile = (file: File, isUser: boolean): void => {
    const error = validateImage(file);
    
    if (error) {
      setErrors(prev => ({
        ...prev,
        [isUser ? 'user' : 'garment']: error
      }));
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string | null;
      if (result) {
        if (isUser) {
          setUserImage(result);
          setErrors(prev => ({ ...prev, user: null }));
        } else {
          setGarmentImage(result);
          setErrors(prev => ({ ...prev, garment: null }));
        }
      }
    };
    reader.readAsDataURL(file);
  };

  const handleDrag = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type !== 'dragleave');
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, isUser: boolean): void => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file, isUser);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();

    if (!userImage || !garmentImage) {
      setErrors({
        user: !userImage ? 'Upload user image' : null,
        garment: !garmentImage ? 'Upload garment image' : null
      });
      return;
    }

    try {
      // Upload images to CDN or backend (simplified)
      // In production, these would be uploaded to S3/CDN first
      await onUpload(userImage, garmentImage);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setErrors({ submit: message });
    }
  };

  return (
    <div className="image-upload">
      <h2>Virtual Try-On</h2>
      
      <form onSubmit={handleSubmit}>
        {/* User Image Upload */}
        <div className="upload-section">
          <label>Your Photo</label>
          
          <div
            className={`upload-area ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={(e) => handleDrop(e, true)}
          >
            {userImage ? (
              <div className="preview">
                <img src={userImage} alt="User" />
                <button
                  type="button"
                  onClick={() => setUserImage(null)}
                  className="remove-btn"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="upload-placeholder">
                <p>📸 Drag image here or click</p>
                <small>JPEG, PNG, or WebP • Max 10MB</small>
              </div>
            )}

            <input
              type="file"
              accept="image/*"
              onChange={(e) => e.target.files && handleFile(e.target.files[0], true)}
              style={{ display: 'none' }}
              id="user-image-input"
            />
          </div>

          <label htmlFor="user-image-input" className="file-input-label">
            {userImage ? 'Change photo' : 'Select photo'}
          </label>

          {errors.user && <p className="error">{errors.user}</p>}
        </div>

        {/* Garment Image Upload */}
        <div className="upload-section">
          <label>Garment Product</label>

          <div
            className={`upload-area ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={(e) => handleDrop(e, false)}
          >
            {garmentImage ? (
              <div className="preview">
                <img src={garmentImage} alt="Garment" />
                <button
                  type="button"
                  onClick={() => setGarmentImage(null)}
                  className="remove-btn"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="upload-placeholder">
                <p>👕 Drag image here or click</p>
                <small>JPEG, PNG, or WebP • Max 10MB</small>
              </div>
            )}

            <input
              type="file"
              accept="image/*"
              onChange={(e) => e.target.files && handleFile(e.target.files[0], false)}
              style={{ display: 'none' }}
              id="garment-image-input"
            />
          </div>

          <label htmlFor="garment-image-input" className="file-input-label">
            {garmentImage ? 'Change product' : 'Select product'}
          </label>

          {errors.garment && <p className="error">{errors.garment}</p>}
        </div>

        <button
          type="submit"
          disabled={!userImage || !garmentImage}
          className="submit-btn"
        >
          Generate Try-On
        </button>

        {errors.submit && <p className="error">{errors.submit}</p>}
      </form>
    </div>
  );
}
