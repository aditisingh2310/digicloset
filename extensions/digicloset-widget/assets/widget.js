/**
 * DigiCloset Virtual Try-On Widget
 * Theme App Extension Version
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    apiBaseUrl: window.DIGICLOSET_API_URL || '/api',
    pollInterval: 2000,
    maxPolls: 150,
    buttonText: 'Try On This Item',
    modalTitle: 'Virtual Try-On',
  };

  // State management
  let currentState = {
    productId: null,
    tryonId: null,
    isProcessing: false,
  };

  // DOM Elements
  let modalElement = null;
  let tryOnButton = null;

  /**
   * Initialize the widget
   */
  function init() {
    const container = document.getElementById('digicloset-tryon-widget');
    if (!container) {
      console.warn('[DigiCloset] Widget container not found');
      return;
    }

    currentState.productId = container.dataset.productId;
    if (!currentState.productId) {
      console.warn('[DigiCloset] Product ID not found');
      return;
    }

    tryOnButton = document.getElementById('digicloset-tryon-button');
    if (tryOnButton) {
      tryOnButton.addEventListener('click', openModal);
    }

    injectModal();
  }

  /**
   * Inject modal HTML
   */
  function injectModal() {
    const modalHTML = `
      <div id="digicloset-modal" class="digicloset-modal" style="display: none;">
        <div class="digicloset-modal-overlay" id="digicloset-modal-overlay"></div>
        <div class="digicloset-modal-content">
          <div class="digicloset-modal-header">
            <h2>${CONFIG.modalTitle}</h2>
            <button class="digicloset-modal-close" id="digicloset-modal-close">&times;</button>
          </div>
          <div class="digicloset-modal-body" id="digicloset-modal-body">
            ${getUploadForm()}
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    modalElement = document.getElementById('digicloset-modal');
    document.getElementById('digicloset-modal-overlay').addEventListener('click', closeModal);
    document.getElementById('digicloset-modal-close').addEventListener('click', closeModal);
  }

  /**
   * Get upload form HTML
   */
  function getUploadForm() {
    return `
      <div class="digicloset-upload-form">
        <div class="digicloset-upload-section">
          <h3>Upload Your Photo</h3>
          <div class="digicloset-drop-zone" id="user-image-drop">
            <input type="file" id="user-image-input" accept="image/*" style="display: none;">
            <div class="digicloset-drop-content" id="user-image-content">
              <p>Drop your photo here or <button type="button" id="user-image-btn">browse</button></p>
            </div>
            <img id="user-image-preview" class="digicloset-preview" style="display: none;" alt="Your photo">
          </div>
        </div>
        <div class="digicloset-upload-section">
          <h3>Garment Image (Auto-filled)</h3>
          <div class="digicloset-garment-preview">
            <img id="garment-image-preview" src="" alt="Product image" style="max-width: 200px;">
          </div>
        </div>
        <button type="button" id="digicloset-submit" class="digicloset-submit-btn" disabled>Generate Try-On</button>
      </div>
    `;
  }

  /**
   * Open modal
   */
  function openModal() {
    if (modalElement) {
      modalElement.style.display = 'block';
      document.body.style.overflow = 'hidden';
      setupEventListeners();
      loadProductImage();
    }
  }

  /**
   * Close modal
   */
  function closeModal() {
    if (modalElement) {
      modalElement.style.display = 'none';
      document.body.style.overflow = '';
      resetModal();
    }
  }

  /**
   * Setup event listeners
   */
  function setupEventListeners() {
    // User image upload
    const userBtn = document.getElementById('user-image-btn');
    const userInput = document.getElementById('user-image-input');
    const userDrop = document.getElementById('user-image-drop');

    if (userBtn && userInput) {
      userBtn.addEventListener('click', () => userInput.click());
      userInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0], true));
    }

    if (userDrop) {
      userDrop.addEventListener('dragover', handleDragOver);
      userDrop.addEventListener('drop', (e) => handleDrop(e, true));
    }

    // Submit button
    const submitBtn = document.getElementById('digicloset-submit');
    if (submitBtn) {
      submitBtn.addEventListener('click', handleSubmit);
    }
  }

  /**
   * Load product image
   */
  function loadProductImage() {
    // Get product image from Shopify's product object
    if (window.product && window.product.featured_image) {
      const img = document.getElementById('garment-image-preview');
      if (img) {
        img.src = window.product.featured_image;
      }
    }
  }

  /**
   * Handle file selection
   */
  function handleFileSelect(file, isUser) {
    if (!file) return;

    const error = validateImage(file);
    if (error) {
      showError(error);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target.result;
      if (isUser) {
        const preview = document.getElementById('user-image-preview');
        const content = document.getElementById('user-image-content');
        if (preview && content) {
          preview.src = result;
          preview.style.display = 'block';
          content.style.display = 'none';
        }
        currentState.userImage = result;
        checkSubmitEnabled();
      }
    };
    reader.readAsDataURL(file);
  }

  /**
   * Handle drag over
   */
  function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-active');
  }

  /**
   * Handle drop
   */
  function handleDrop(e, isUser) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-active');
    const file = e.dataTransfer.files[0];
    if (file && isUser) {
      handleFileSelect(file, true);
    }
  }

  /**
   * Validate image
   */
  function validateImage(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!validTypes.includes(file.type)) {
      return 'Invalid file type. Use JPEG, PNG, or WebP';
    }

    if (file.size > maxSize) {
      return 'File too large. Max 10MB';
    }

    return null;
  }

  /**
   * Check if submit should be enabled
   */
  function checkSubmitEnabled() {
    const submitBtn = document.getElementById('digicloset-submit');
    if (submitBtn) {
      submitBtn.disabled = !currentState.userImage;
    }
  }

  /**
   * Handle submit
   */
  async function handleSubmit() {
    if (!currentState.userImage) return;

    setProcessing(true);

    try {
      // Upload images first with timeout
      const uploadTimeout = 30000; // 30 seconds
      const userImageUrl = await Promise.race([
        uploadImage(currentState.userImage),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Upload timeout')), uploadTimeout))
      ]);
      const garmentImageUrl = document.getElementById('garment-image-preview').src;

      // Start try-on generation with timeout
      const generateTimeout = 60000; // 60 seconds
      const response = await Promise.race([
        fetch(`${CONFIG.apiBaseUrl}/v1/try-on/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_image_url: userImageUrl,
            garment_image_url: garmentImageUrl,
            product_id: currentState.productId,
            category: 'upper_body'
          })
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Generation request timeout')), generateTimeout))
      ]);

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.status}`);
      }

      const data = await response.json();
      currentState.tryonId = data.id;

      // Start polling
      pollResult(data.id);
    } catch (err) {
      console.error('[DigiCloset] Submit error:', err);
      showError(err.message || 'Service temporarily unavailable. Please try again later.');
      setProcessing(false);
    }
  }

  /**
   * Upload image (placeholder - implement actual upload)
   */
  async function uploadImage(dataUrl) {
    // In production, upload to S3 and return signed URL
    return dataUrl; // Placeholder
  }

  /**
   * Poll for result
   */
  async function pollResult(tryonId) {
    let attempt = 0;

    const poll = async () => {
      try {
        const response = await Promise.race([
          fetch(`${CONFIG.apiBaseUrl}/v1/try-on/${tryonId}`),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Poll timeout')), 10000))
        ]);
        const data = await response.json();

        if (data.status === 'completed') {
          showResult(data);
          return;
        } else if (data.status === 'failed') {
          throw new Error(data.error || 'Generation failed');
        }

        if (attempt < CONFIG.maxPolls) {
          attempt++;
          setTimeout(poll, CONFIG.pollInterval);
        } else {
          throw new Error('Generation timeout - please try again later');
        }
      } catch (err) {
        console.error('[DigiCloset] Poll error:', err);
        showError(err.message || 'Service temporarily unavailable. Please try again later.');
        setProcessing(false);
      }
    };

    poll();
  }

  /**
   * Set processing state
   */
  function setProcessing(processing) {
    currentState.isProcessing = processing;
    const body = document.getElementById('digicloset-modal-body');

    if (processing) {
      body.innerHTML = `
        <div class="digicloset-processing">
          <div class="digicloset-spinner"></div>
          <p>Generating your virtual try-on...</p>
        </div>
      `;
    }
  }

  /**
   * Show result
   */
  function showResult(data) {
    const body = document.getElementById('digicloset-modal-body');
    body.innerHTML = `
      <div class="digicloset-result">
        <h3>Try-On Complete!</h3>
        <img src="${data.generated_image_url}" alt="Virtual try-on" style="max-width: 100%;">
        <div class="digicloset-actions">
          <button onclick="closeModal()">Close</button>
          <button onclick="resetModal()">Try Another</button>
        </div>
      </div>
    `;
  }

  /**
   * Show error
   */
  function showError(message) {
    const body = document.getElementById('digicloset-modal-body');
    body.innerHTML = `
      <div class="digicloset-error">
        <p>${message}</p>
        <button onclick="resetModal()">Try Again</button>
      </div>
    `;
  }

  /**
   * Reset modal
   */
  function resetModal() {
    currentState = {
      productId: currentState.productId,
      tryonId: null,
      isProcessing: false,
    };

    const body = document.getElementById('digicloset-modal-body');
    body.innerHTML = getUploadForm();
    setupEventListeners();
    loadProductImage();
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();