import { useState } from 'react';
import './ResultDisplay.css';

interface TryOnResult {
  image_url?: string;
  generated_image_url?: string;
  id: string;
  processing_time?: number;
  [key: string]: unknown;
}

interface ResultDisplayProps {
  result: TryOnResult;
  onRetry: () => void;
}

/**
 * ResultDisplay Component
 *
 * Shows:
 * - Generated try-on image
 * - Processing time
 * - Action buttons (share, download, add to cart)
 */
export default function ResultDisplay({ result, onRetry }: ResultDisplayProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const imageUrl = result.image_url || result.generated_image_url || '';

  const handleDownload = async () => {
    setIsDownloading(true);

    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const contentType = response.headers.get('content-type') || '';
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tryon-${result.id}.${contentType.includes('svg') ? 'svg' : 'png'}`;
      a.click();
      window.URL.revokeObjectURL(url);
      setMessage('Image saved to your device.');
    } catch (err) {
      console.error('Download failed:', err);
      setMessage('Download failed. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'Virtual Try-On',
          text: 'Check out this DigiCloset try-on preview.',
          url: imageUrl,
        });
        setMessage('Share sheet opened.');
        return;
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(imageUrl);
        setMessage('Image link copied to clipboard.');
        return;
      }

      setMessage('Sharing is not supported in this browser.');
    } catch (err) {
      console.error('Share failed:', err);
      setMessage('Sharing was canceled or unavailable.');
    }
  };

  const handleAddToCart = () => {
    const event = new CustomEvent('tryon:addToCart', {
      detail: { imageSrc: imageUrl },
    });
    window.dispatchEvent(event);
    setMessage('The result was passed to your cart flow.');
  };

  return (
    <div className="result-display">
      <p className="result-display__eyebrow">Step 3</p>
      <h2>Your try-on result is ready</h2>

      <div className="result-image-container">
        <img src={imageUrl} alt="Try-on result" className="result-image" />
      </div>

      <div className="result-info">
        <p className="processing-time">
          Generated in {result.processing_time || 0}s
        </p>
        <p className="result-caption">
          Use this preview to build shopper confidence, save it for later, or
          route it into your cart experience.
        </p>
      </div>

      <div className="action-buttons">
        <button
          onClick={handleDownload}
          className="btn btn-primary"
          title="Download as image"
          disabled={isDownloading}
        >
          {isDownloading ? 'Saving...' : 'Download'}
        </button>

        <button
          onClick={handleShare}
          className="btn btn-secondary"
          title="Share with friends"
        >
          Share
        </button>

        <button
          onClick={handleAddToCart}
          className="btn btn-secondary"
          title="Add to cart"
        >
          Add to cart
        </button>
      </div>

      {message ? <p className="result-message">{message}</p> : null}

      <button onClick={onRetry} className="btn btn-secondary">
        Try Another Item
      </button>

      <div className="result-footer">
        <small>Try-On ID: {result.id}</small>
      </div>
    </div>
  );
}
