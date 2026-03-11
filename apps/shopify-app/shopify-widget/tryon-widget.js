/**
 * DigiCloset Virtual Try-On Widget
 * 
 * Embeds a "Try On" button on Shopify product pages with modal for
 * uploading customer images and viewing virtual try-on results.
 * 
 * Usage:
 *   <script src="https://digicloset.app/widget/tryon-widget.js"></script>
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    apiBaseUrl: window.DIGICLOSET_API_URL || 'https://api.digicloset.app',
    pollInterval: 2000, // 2 seconds
    maxPolls: 150, // 5 minutes max
    buttonText: 'Try On This Item',
    buttonColor: '#000000',
    modalTitle: 'Virtual Try-On',
  };

  // State management
  let currentState = {
    productId: null,
    tryon: null,
    isProcessing: false,
  };

  // ============ DOM Elements ============

  let modalElement = null;
  let tryOnButton = null;

  /**
   * Initialize the widget on page load
   */
  function init() {
    // Extract product ID from page context
    const productId = extractProductId();
    if (!productId) {
      console.warn('[DigiCloset] Could not determine product ID');
      return;
    }

    currentState.productId = productId;

    // Inject styles
    injectStyles();

    // Create and insert button
    createTryOnButton();

    // Create modal
    createModal();

    // Add event listeners
    attachEventListeners();

    console.log('[DigiCloset] Widget initialized for product:', productId);
  }

  // ============ DOM Creation ============

  /**
   * Create the "Try On" button
   */
  function createTryOnButton() {
    tryOnButton = document.createElement('button');
    tryOnButton.id = 'digicloset-try-on-btn';
    tryOnButton.textContent = CONFIG.buttonText;
    tryOnButton.style.backgroundColor = CONFIG.buttonColor;
    tryOnButton.className = 'digicloset-try-on-button';

    // Find insertion point (usually near "Add to Cart" button)
    const addToCartBtn = document.querySelector('[name="add"]') ||
                        document.querySelector('button[type="submit"]');

    if (addToCartBtn && addToCartBtn.parentNode) {
      addToCartBtn.parentNode.insertBefore(tryOnButton, addToCartBtn.nextSibling);
    } else {
      // Fallback: insert at end of product section
      const productSection = document.querySelector('.product-section') ||
                           document.querySelector('[data-section-type="product"]');
      if (productSection) {
        productSection.appendChild(tryOnButton);
      }
    }
  }

  /**
   * Create the modal dialog for try-on
   */
  function createModal() {
    modalElement = document.createElement('div');
    modalElement.id = 'digicloset-modal';
    modalElement.className = 'digicloset-modal hidden';

    modalElement.innerHTML = `
      <div class="digicloset-modal-content">
        <div class="digicloset-modal-header">
          <h2>${CONFIG.modalTitle}</h2>
          <button class="digicloset-close-btn" aria-label="Close">&times;</button>
        </div>

        <div class="digicloset-modal-body">
          <!-- Upload Section -->
          <div class="digicloset-section digicloset-upload-section" id="upload-section">
            <div class="digicloset-form-group">
              <label for="user-image-input">Your Photo</label>
              <div class="digicloset-image-upload">
                <input
                  type="file"
                  id="user-image-input"
                  class="digicloset-file-input"
                  accept="image/*"
                  aria-label="Upload your photo"
                />
                <p>Upload a clear photo of yourself</p>
              </div>
              <div id="user-image-preview" class="digicloset-image-preview hidden"></div>
            </div>
          </div>

          <!-- Processing Section -->
          <div class="digicloset-section digicloset-processing-section hidden" id="processing-section">
            <div class="digicloset-spinner"></div>
            <p>Generating your try-on...</p>
            <p class="digicloset-processing-time" id="processing-time"></p>
          </div>

          <!-- Result Section -->
          <div class="digicloset-section digicloset-result-section hidden" id="result-section">
            <div class="digicloset-result-image">
              <img id="result-image" src="" alt="Try-on result" />
            </div>
            <div class="digicloset-result-info">
              <p id="result-message">Your try-on is ready!</p>
              <button class="digicloset-retry-btn" id="retry-btn">Try Another Photo</button>
              <a class="digicloset-share-btn" id="share-btn" target="_blank">Share Result</a>
            </div>
          </div>

          <!-- Error Section -->
          <div class="digicloset-section digicloset-error-section hidden" id="error-section">
            <p class="digicloset-error-message" id="error-message"></p>
            <button class="digicloset-retry-btn" id="error-retry-btn">Try Again</button>
          </div>
        </div>

        <div class="digicloset-modal-footer">
          <button class="digicloset-generate-btn" id="generate-btn" disabled>
            Generate Try-On
          </button>
          <p class="digicloset-footer-text">
            Powered by <strong>DigiCloset</strong> AI
          </p>
        </div>
      </div>
    `;

    document.body.appendChild(modalElement);
  }

  // ============ Event Handlers ============

  /**
   * Attach event listeners to interactive elements
   */
  function attachEventListeners() {
    // Open modal
    tryOnButton.addEventListener('click', openModal);

    // Close modal
    const closeBtn = modalElement.querySelector('.digicloset-close-btn');
    closeBtn.addEventListener('click', closeModal);

    // File input change
    const fileInput = document.getElementById('user-image-input');
    fileInput.addEventListener('change', handleImageUpload);

    // Generate button
    const generateBtn = document.getElementById('generate-btn');
    generateBtn.addEventListener('click', generateTryOn);

    // Retry buttons
    document.getElementById('retry-btn')?.addEventListener('click', resetModal);
    document.getElementById('error-retry-btn')?.addEventListener('click', resetModal);

    // Close on outside click
    modalElement.addEventListener('click', (e) => {
      if (e.target === modalElement) closeModal();
    });
  }

  /**
   * Open the try-on modal
   */
  function openModal() {
    modalElement.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  /**
   * Close the try-on modal
   */
  function closeModal() {
    modalElement.classList.add('hidden');
    document.body.style.overflow = 'auto';
  }

  /**
   * Handle user image upload
   */
  function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file
    if (!file.type.startsWith('image/')) {
      showError('Please upload an image file');
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB
      showError('Image must be less than 10MB');
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const preview = document.getElementById('user-image-preview');
      preview.innerHTML = `<img src="${e.target.result}" alt="Preview" />`;
      preview.classList.remove('hidden');

      // Enable generate button
      document.getElementById('generate-btn').disabled = false;

      // Store image data
      currentState.imageFile = file;
      currentState.imageUrl = e.target.result;
    };

    reader.readAsDataURL(file);
  }

  /**
   * Generate try-on image
   */
  async function generateTryOn() {
    if (!currentState.imageFile) {
      showError('Please upload an image first');
      return;
    }

    currentState.isProcessing = true;
    showProcessing();

    try {
      // Upload image to server (using FormData for multipart)
      const formData = new FormData();
      formData.append('user_image', currentState.imageFile);
      formData.append('product_id', currentState.productId);

      const uploadResponse = await fetch(
        `${CONFIG.apiBaseUrl}/api/v1/try-on/generate`,
        {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`,
          },
        }
      );

      if (!uploadResponse.ok) {
        const error = await uploadResponse.json();
        throw new Error(error.detail || 'Failed to generate try-on');
      }

      const result = await uploadResponse.json();
      currentState.tryon = result;

      // Poll for result
      await pollTryOnResult(result.id);

    } catch (error) {
      showError(error.message || 'Failed to generate try-on. Please try again.');
    } finally {
      currentState.isProcessing = false;
    }
  }

  /**
   * Poll for try-on generation result
   */
  async function pollTryOnResult(tryonId) {
    let pollCount = 0;

    while (pollCount < CONFIG.maxPolls) {
      try {
        const response = await fetch(
          `${CONFIG.apiBaseUrl}/api/v1/try-on/${tryonId}`,
          {
            headers: {
              'Authorization': `Bearer ${getAuthToken()}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to check status');
        }

        const data = await response.json();

        switch (data.status) {
          case 'completed':
            showResult(data.image_url, data.processing_time);
            return;

          case 'failed':
            throw new Error(data.error || 'Try-on generation failed');

          case 'processing':
          case 'pending':
            // Update processing message
            const processingTime = document.getElementById('processing-time');
            processingTime.textContent = `Processing time: ${(data.processing_time || (pollCount * 2)).toFixed(1)}s`;
            break;
        }

        // Wait before next poll with exponential backoff (max 5 seconds)
        const delay = Math.min(CONFIG.pollInterval * (1 + Math.random() * 0.1), 5000);
        await new Promise(resolve => setTimeout(resolve, delay));
        pollCount++;

      } catch (error) {
        if (pollCount < 3) {
          // Retry a few times silently
          await new Promise(resolve => setTimeout(resolve, CONFIG.pollInterval));
          pollCount++;
        } else {
          showError(error.message);
          return;
        }
      }
    }

    showError('Try-on generation took too long. Please try again.');
  }

  /**
   * Show processing state
   */
  function showProcessing() {
    document.getElementById('upload-section').classList.add('hidden');
    document.getElementById('result-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('processing-section').classList.remove('hidden');
    document.getElementById('generate-btn').disabled = true;
  }

  /**
   * Show result
   */
  function showResult(imageUrl, processingTime) {
    document.getElementById('result-image').src = imageUrl;
    document.getElementById('result-message').textContent = `Generated in ${processingTime?.toFixed(1) || '?'}s`;

    // Set share URL
    const shareBtn = document.getElementById('share-btn');
    const shareUrl = new URL(currentState.tryon.share_url || window.location.href);
    shareBtn.href = `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=Check%20out%20my%20virtual%20try-on%20from%20DigiCloset!`;

    document.getElementById('upload-section').classList.add('hidden');
    document.getElementById('processing-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('result-section').classList.remove('hidden');
    document.getElementById('generate-btn').disabled = true;
  }

  /**
   * Show error message
   */
  function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('processing-section').classList.add('hidden');
    document.getElementById('result-section').classList.add('hidden');
    document.getElementById('error-section').classList.remove('hidden');
  }

  /**
   * Reset modal to initial state
   */
  function resetModal() {
    document.getElementById('user-image-input').value = '';
    document.getElementById('user-image-preview').classList.add('hidden');
    document.getElementById('user-image-preview').innerHTML = '';
    document.getElementById('upload-section').classList.remove('hidden');
    document.getElementById('result-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('processing-section').classList.add('hidden');
    document.getElementById('generate-btn').disabled = true;
    currentState.imageFile = null;
    currentState.imageUrl = null;
  }

  // ============ Utility Functions ============

  /**
   * Extract product ID from page
   */
  function extractProductId() {
    // Try different Shopify variations
    const metaTag = document.querySelector('meta[property="product:id"]');
    if (metaTag) {
      return metaTag.getAttribute('content').split('/').pop();
    }

    // Try from product form
    const productForm = document.querySelector('form[id*="product"]');
    if (productForm) {
      const input = productForm.querySelector('input[name="id"]');
      if (input) return input.value;
    }

    // Try from page URL or data attributes
    const productData = document.querySelector('[data-product-id]');
    if (productData) {
      return productData.getAttribute('data-product-id');
    }

    return null;
  }

  /**
   * Get authentication token
   */
  function getAuthToken() {
    // Get from localStorage, sessionStorage, or cookie
    return localStorage.getItem('digicloset_token') ||
           sessionStorage.getItem('digicloset_token') ||
           getCookie('digicloset_token') ||
           '';
  }

  /**
   * Get cookie value by name
   */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  /**
   * Inject CSS styles
   */
  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      /* Try-On Button */
      .digicloset-try-on-button {
        display: inline-block;
        padding: 12px 24px;
        margin-top: 10px;
        background-color: #000;
        color: #fff;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .digicloset-try-on-button:hover {
        background-color: #333;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      }

      /* Modal Styles */
      .digicloset-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
      }

      .digicloset-modal.hidden {
        display: none;
      }

      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }

      .digicloset-modal-content {
        background: white;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        max-width: 600px;
        width: 90%;
        max-height: 90vh;
        overflow-y: auto;
      }

      .digicloset-modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        border-bottom: 1px solid #eee;
      }

      .digicloset-modal-header h2 {
        margin: 0;
        font-size: 20px;
      }

      .digicloset-close-btn {
        background: none;
        border: none;
        font-size: 28px;
        cursor: pointer;
        color: #999;
        transition: color 0.3s ease;
      }

      .digicloset-close-btn:hover {
        color: #333;
      }

      .digicloset-modal-body {
        padding: 20px;
        min-height: 200px;
      }

      .digicloset-modal-footer {
        padding: 20px;
        border-top: 1px solid #eee;
        text-align: center;
      }

      /* Sections */
      .digicloset-section {
        margin-bottom: 20px;
      }

      .digicloset-section.hidden {
        display: none;
      }

      /* Form Groups */
      .digicloset-form-group {
        margin-bottom: 20px;
      }

      .digicloset-form-group label {
        display: block;
        margin-bottom: 10px;
        font-weight: 600;
        color: #333;
      }

      /* File Upload */
      .digicloset-image-upload {
        border: 2px dashed #ddd;
        border-radius: 4px;
        padding: 30px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
      }

      .digicloset-image-upload:hover {
        border-color: #999;
        background-color: #f9f9f9;
      }

      .digicloset-file-input {
        display: none;
      }

      .digicloset-image-preview {
        margin-top: 15px;
        text-align: center;
      }

      .digicloset-image-preview img {
        max-width: 100%;
        max-height: 300px;
        border-radius: 4px;
      }

      /* Spinner */
      .digicloset-spinner {
        border: 3px solid #f3f3f3;
        border-top: 3px solid #333;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 30px auto;
      }

      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      .digicloset-processing-section p {
        text-align: center;
        color: #666;
      }

      .digicloset-processing-time {
        font-size: 12px;
        color: #999;
      }

      /* Result */
      .digicloset-result-image {
        text-align: center;
        margin-bottom: 20px;
      }

      .digicloset-result-image img {
        max-width: 100%;
        max-height: 400px;
        border-radius: 4px;
      }

      .digicloset-result-info {
        text-align: center;
      }

      /* Buttons */
      .digicloset-generate-btn,
      .digicloset-retry-btn {
        display: inline-block;
        padding: 12px 24px;
        background-color: #000;
        color: #fff;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        margin: 0 5px;
        transition: all 0.3s ease;
      }

      .digicloset-generate-btn:disabled {
        background-color: #ccc;
        cursor: not-allowed;
      }

      .digicloset-generate-btn:hover:not(:disabled),
      .digicloset-retry-btn:hover {
        background-color: #333;
      }

      .digicloset-share-btn {
        display: inline-block;
        padding: 12px 24px;
        background-color: #1da1f2;
        color: #fff;
        text-decoration: none;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 600;
        margin: 0 5px;
        transition: background-color 0.3s ease;
      }

      .digicloset-share-btn:hover {
        background-color: #1a91da;
      }

      /* Error */
      .digicloset-error-section {
        background-color: #ffe6e6;
        padding: 15px;
        border-radius: 4px;
        border-left: 4px solid #ff0000;
      }

      .digicloset-error-message {
        color: #d32f2f;
        margin: 0 0 15px 0;
      }

      /* Footer */
      .digicloset-footer-text {
        font-size: 12px;
        color: #999;
        margin: 0;
      }
    `;

    document.head.appendChild(style);
  }

  // ============ Initialization ============

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
