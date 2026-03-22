/**
 * DigiCloset Virtual Try-On Widget (Improved UX Version)
 */

(function() {
  'use strict';

  const CONFIG = {
    apiBaseUrl: window.DIGICLOSET_API_URL || 'https://api.digicloset.app',
    pollInterval: 2000,
    maxPolls: 150,
    buttonText: '✨ Try This On You',
    modalTitle: '👗 See it on you instantly',
  };

  let currentState = {
    productId: null,
    tryon: null,
    isProcessing: false,
  };

  let modalElement = null;
  let tryOnButton = null;

  function init() {
    const productId = extractProductId();
    if (!productId) return;

    currentState.productId = productId;

    injectStyles();
    createTryOnButton();
    createModal();
    attachEventListeners();
  }

  function createTryOnButton() {
    tryOnButton = document.createElement('button');
    tryOnButton.textContent = CONFIG.buttonText;
    tryOnButton.className = 'digicloset-try-on-button';

    const addToCartBtn = document.querySelector('[name="add"]') ||
                        document.querySelector('button[type="submit"]');

    if (addToCartBtn?.parentNode) {
      addToCartBtn.parentNode.insertBefore(tryOnButton, addToCartBtn.nextSibling);
    }
  }

  function createModal() {
    modalElement = document.createElement('div');
    modalElement.className = 'digicloset-modal hidden';

    modalElement.innerHTML = `
      <div class="digicloset-modal-content">
        <div class="digicloset-modal-header">
          <h2>${CONFIG.modalTitle}</h2>
          <button class="digicloset-close-btn">&times;</button>
        </div>

        <div class="digicloset-modal-body">

          <div class="digicloset-steps">
            1. Upload Photo → 2. Generate → 3. View Result
          </div>

          <div id="upload-section">
            <input type="file" id="user-image-input" accept="image/*"/>
            <div id="user-image-preview" class="hidden"></div>
            <p class="digicloset-trust-text">
              🔒 Your image is processed securely and deleted within 24 hours.
            </p>
          </div>

          <div id="processing-section" class="hidden">
            <div class="digicloset-spinner"></div>
            <p>Generating your try-on...</p>
            <p id="processing-time"></p>
          </div>

          <div id="result-section" class="hidden">
            <img id="result-image"/>
            <p id="result-message"></p>
          </div>

          <div id="error-section" class="hidden">
            <p id="error-message"></p>
          </div>

        </div>

        <div class="digicloset-modal-footer">
          <button id="generate-btn" disabled>Generate Try-On</button>
        </div>
      </div>
    `;

    document.body.appendChild(modalElement);
  }

  function attachEventListeners() {
    tryOnButton.addEventListener('click', () => {
      modalElement.classList.remove('hidden');
    });

    modalElement.querySelector('.digicloset-close-btn')
      .addEventListener('click', () => modalElement.classList.add('hidden'));

    document.getElementById('user-image-input')
      .addEventListener('change', handleImageUpload);

    document.getElementById('generate-btn')
      .addEventListener('click', generateTryOn);
  }

  function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      showError('Please upload an image file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const preview = document.getElementById('user-image-preview');
      preview.innerHTML = `<img src="${e.target.result}" /> 
        <p style="color:green;font-size:12px;">✓ Image uploaded</p>`;
      preview.classList.remove('hidden');

      document.getElementById('generate-btn').disabled = false;
      currentState.imageFile = file;
    };
    reader.readAsDataURL(file);
  }

  async function generateTryOn() {
    const btn = document.getElementById('generate-btn');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    showProcessing();

    try {
      const formData = new FormData();
      formData.append('user_image', currentState.imageFile);
      formData.append('product_id', currentState.productId);

      const res = await fetch(`${CONFIG.apiBaseUrl}/api/v1/try-on/generate`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      await pollTryOnResult(data.id);

    } catch (err) {
      showError(err.message);
    }
  }

  async function pollTryOnResult(id) {
    let count = 0;

    while (count < CONFIG.maxPolls) {
      const res = await fetch(`${CONFIG.apiBaseUrl}/api/v1/try-on/${id}`);
      const data = await res.json();

      if (data.status === 'completed') {
        showResult(data.image_url, data.processing_time);
        return;
      }

      await new Promise(r => setTimeout(r, CONFIG.pollInterval));
      count++;
    }

    showError('Timeout. Try again.');
  }

  function showProcessing() {
    toggleSections('processing');
  }

  function showResult(img, time) {
    document.getElementById('result-image').src = img;
    document.getElementById('result-message').textContent =
      `✨ Your look is ready! Generated in ${time?.toFixed(1) || '?'}s`;

    toggleSections('result');
  }

  function showError(msg) {
    document.getElementById('error-message').textContent =
      msg + " Try a clear front-facing photo.";
    toggleSections('error');
  }

  function toggleSections(active) {
    ['upload','processing','result','error'].forEach(s => {
      document.getElementById(`${s}-section`)
        .classList.toggle('hidden', s !== active);
    });
  }

  function extractProductId() {
    const input = document.querySelector('input[name=\"id\"]');
    return input?.value || null;
  }

  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .digicloset-try-on-button {
        width:100%;
        padding:12px;
        background:#000;
        color:#fff;
        cursor:pointer;
      }

      .digicloset-modal {
        position:fixed;
        top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,0.5);
        display:flex;
        align-items:center;
        justify-content:center;
      }

      .hidden { display:none; }

      .digicloset-modal-content {
        background:#fff;
        padding:20px;
        max-width:500px;
        width:95%;
      }

      .digicloset-spinner {
        width:40px;height:40px;
        border:4px solid #ccc;
        border-top:4px solid #000;
        border-radius:50%;
        animation:spin 1s linear infinite;
      }

      @keyframes spin {
        to { transform: rotate(360deg); }
      }

      .digicloset-steps {
        font-size:12px;
        color:#888;
        margin-bottom:10px;
      }

      .digicloset-trust-text {
        font-size:12px;
        color:#666;
      }
    `;
    document.head.appendChild(style);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
