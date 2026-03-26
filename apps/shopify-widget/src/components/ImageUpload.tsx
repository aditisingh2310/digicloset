import { useRef, useState } from 'react';
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
  const [activeDropzone, setActiveDropzone] = useState<'user' | 'garment' | null>(
    null
  );
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const userInputRef = useRef<HTMLInputElement | null>(null);
  const garmentInputRef = useRef<HTMLInputElement | null>(null);

  const validateImage = (file: File): string | null => {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 10 * 1024 * 1024;

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
      setErrors((prev) => ({
        ...prev,
        [isUser ? 'user' : 'garment']: error,
      }));
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string | null;

      if (!result) {
        return;
      }

      if (isUser) {
        setUserImage(result);
        setErrors((prev) => ({ ...prev, user: null, submit: null }));
        return;
      }

      setGarmentImage(result);
      setErrors((prev) => ({ ...prev, garment: null, submit: null }));
    };
    reader.readAsDataURL(file);
  };

  const handleDrag = (
    e: React.DragEvent<HTMLDivElement>,
    zone: 'user' | 'garment'
  ): void => {
    e.preventDefault();
    e.stopPropagation();

    if (e.type === 'dragleave') {
      setActiveDropzone((current) => (current === zone ? null : current));
      return;
    }

    setActiveDropzone(zone);
  };

  const handleDrop = (
    e: React.DragEvent<HTMLDivElement>,
    isUser: boolean
  ): void => {
    e.preventDefault();
    e.stopPropagation();
    setActiveDropzone(null);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file, isUser);
    }
  };

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();

    if (!userImage || !garmentImage) {
      setErrors({
        user: !userImage ? 'Upload a customer photo' : null,
        garment: !garmentImage ? 'Upload a garment image' : null,
      });
      return;
    }

    try {
      await onUpload(userImage, garmentImage);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setErrors({ submit: message });
    }
  };

  const openPicker = (zone: 'user' | 'garment') => {
    if (zone === 'user') {
      userInputRef.current?.click();
      return;
    }

    garmentInputRef.current?.click();
  };

  const clearImage = (zone: 'user' | 'garment') => {
    if (zone === 'user') {
      setUserImage(null);
    } else {
      setGarmentImage(null);
    }

    setErrors((prev) => ({
      ...prev,
      [zone]: null,
      submit: null,
    }));
  };

  const renderUploadPanel = ({
    zone,
    title,
    helper,
    image,
    error,
  }: {
    zone: 'user' | 'garment';
    title: string;
    helper: string;
    image: string | null;
    error: string | null | undefined;
  }) => (
    <div className="upload-section">
      <div className="upload-section__header">
        <h3>{title}</h3>
        <p>{helper}</p>
      </div>

      <div
        className={`upload-area ${activeDropzone === zone ? 'active' : ''}`}
        onDragEnter={(e) => handleDrag(e, zone)}
        onDragLeave={(e) => handleDrag(e, zone)}
        onDragOver={(e) => handleDrag(e, zone)}
        onDrop={(e) => handleDrop(e, zone === 'user')}
        onClick={() => openPicker(zone)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openPicker(zone);
          }
        }}
        role="button"
        tabIndex={0}
      >
        {image ? (
          <div className="preview">
            <img
              src={image}
              alt={zone === 'user' ? 'Customer upload' : 'Garment upload'}
            />
            <div className="preview-actions">
              <button
                type="button"
                className="file-action-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  openPicker(zone);
                }}
              >
                Replace
              </button>
              <button
                type="button"
                className="remove-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  clearImage(zone);
                }}
              >
                Remove
              </button>
            </div>
          </div>
        ) : (
          <div className="upload-placeholder">
            <p>Drag and drop an image here</p>
            <small>or click to browse. JPEG, PNG, WebP. Up to 10 MB.</small>
          </div>
        )}

        <input
          ref={zone === 'user' ? userInputRef : garmentInputRef}
          type="file"
          accept="image/*"
          onChange={(e) =>
            e.target.files && handleFile(e.target.files[0], zone === 'user')
          }
          style={{ display: 'none' }}
        />
      </div>

      {error ? <p className="error">{error}</p> : null}
    </div>
  );

  return (
    <div className="image-upload">
      <div className="image-upload__header">
        <p className="image-upload__eyebrow">Step 1</p>
        <h2>Start with two clear images</h2>
        <p>
          Add one customer photo and one product image. Cleaner inputs usually
          give cleaner drape, edges, and lighting in the final preview.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="image-upload__grid">
          {renderUploadPanel({
            zone: 'user',
            title: 'Customer photo',
            helper: 'Use a front-facing image with even lighting and visible shoulders.',
            image: userImage,
            error: errors.user,
          })}

          {renderUploadPanel({
            zone: 'garment',
            title: 'Garment image',
            helper: 'Use the clean product shot shoppers see on the product page.',
            image: garmentImage,
            error: errors.garment,
          })}
        </div>

        <div className="image-upload__footer">
          <div className="image-upload__note">
            <strong>Ready for generation</strong>
            <p>
              {userImage && garmentImage
                ? 'Both images are uploaded. Generate the preview when you are ready.'
                : 'Upload both images to unlock the try-on preview.'}
            </p>
          </div>

          <button
            type="submit"
            disabled={!userImage || !garmentImage}
            className="submit-btn"
          >
            Generate preview
          </button>
        </div>

        {errors.submit ? <p className="error">{errors.submit}</p> : null}
      </form>
    </div>
  );
}
